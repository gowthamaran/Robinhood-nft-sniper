from __future__ import annotations

import asyncio
import getpass
import json
import os
import platform
import shutil
import statistics
import time
from collections.abc import Sized
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import typer
from eth_account import Account
from eth_account.signers.local import LocalAccount
from pydantic import HttpUrl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sniper.alerts.telegram import notify
from sniper.config import (
    AppConfig,
    LimitSettings,
    RPCSettings,
    TargetSettings,
    TelegramSettings,
    WalletSettings,
    ensure_layout,
    load_config,
    save_config,
)
from sniper.contract.analyzer import load_abi, resolve_function, validate_contract_address
from sniper.mint.engine import MintEngine
from sniper.models import ExecutionMode
from sniper.network.robinhood import get_network
from sniper.opensea import OpenSeaClient, OpenSeaError, parse_opensea_mint_url
from sniper.rpc.client import RPCClient, RPCPool
from sniper.rpc.websocket import probe_new_heads
from sniper.security.audit import audit_permissions
from sniper.security.redaction import abbreviated, redact
from sniper.service.systemd import install_unit, systemctl
from sniper.setup.easy import (
    SetupInputError,
    download_abi,
    function_signature,
    mint_candidates,
    parse_abi_input,
)
from sniper.storage import StateStore
from sniper.wallet.keystore import create_keystore, load_local_account

app = typer.Typer(no_args_is_help=True, help="Security-first Robinhood Chain NFT sniper")
config_app = typer.Typer(help="Inspect or update configuration")
wallet_app = typer.Typer(help="Inspect or replace the local encrypted wallet")
target_app = typer.Typer(help="Configure a mint target")
service_app = typer.Typer(help="Manage the systemd service")
app.add_typer(config_app, name="config")
app.add_typer(wallet_app, name="wallet")
app.add_typer(target_app, name="target")
app.add_typer(service_app, name="service")
console = Console()


def ask(prompt: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = str(
        typer.prompt(f"{prompt}{suffix}", default=default or "", show_default=False)
    ).strip()
    if not value:
        raise typer.BadParameter("A value is required")
    return value


def choose(title: str, options: list[str]) -> int:
    console.print(f"\n[bold]{title}[/bold]")
    for index, option in enumerate(options, start=1):
        console.print(f"  [cyan]{index}[/cyan]) {option}")
    while True:
        raw = typer.prompt("Press a number").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)
        console.print(f"[yellow]Enter a number from 1 to {len(options)}.[/yellow]")


async def validate_rpc(url: str, chain_id: int) -> float:
    client = RPCClient(url)
    started = time.perf_counter()
    try:
        actual = int(await client.call("eth_chainId"), 16)
        await client.call("eth_blockNumber")
    finally:
        await client.close()
    if actual != chain_id:
        raise typer.BadParameter(f"RPC returned chain {actual}; expected {chain_id}")
    return (time.perf_counter() - started) * 1_000


@app.command()
def setup() -> None:
    """Interactive, testnet-first secure setup wizard."""
    root = ensure_layout()
    console.print(Panel("Use a dedicated low-value wallet. The key stays on this VPS."))
    network_name_raw = ask(
        "Network - WHAT: selects real/test funds; RECOMMENDED: testnet; INPUT",
        default="testnet",
    ).lower()
    if network_name_raw not in {"testnet", "mainnet"}:
        raise typer.BadParameter("Network must be testnet or mainnet")
    network_name = cast(Literal["testnet", "mainnet"], network_name_raw)
    network = get_network(network_name)
    if network_name == "mainnet" and ask("Type MAINNET to accept real-funds risk") != "MAINNET":
        raise typer.Abort()

    primary = ask(
        "Primary HTTPS RPC - WHAT: reads/simulates/submits; EXAMPLE: provider URL; INPUT",
        default=network.public_rpc,
    )
    latency = asyncio.run(validate_rpc(primary, network.chain_id))
    console.print(f"RPC validated: chain {network.chain_id}, {latency:.1f} ms")
    backup_text = typer.prompt(
        "Backup RPCs - WHAT: failover; EXAMPLE: url1,url2; DEFAULT: none", default=""
    ).strip()
    backups = [item.strip() for item in backup_text.split(",") if item.strip()]
    for url in backups:
        asyncio.run(validate_rpc(url, network.chain_id))
    websocket = (
        typer.prompt(
            "WebSocket RPC - WHAT: new-head trigger; EXAMPLE: wss://provider; may skip",
            default="",
        ).strip()
        or None
    )
    if websocket:
        subscription = asyncio.run(probe_new_heads(websocket))
        console.print(f"WebSocket newHeads validated: {abbreviated(subscription)}")

    console.print("Enter the private key into this hidden VPS prompt. It is never transmitted.")
    private_key = getpass.getpass("Dedicated mint-wallet private key: ").strip()
    password = getpass.getpass("New keystore password (12+ chars): ")
    confirmation = getpass.getpass("Repeat keystore password: ")
    if password != confirmation:
        raise typer.BadParameter("Passwords do not match")
    keystore_path = root / "secrets" / "wallet.json"
    address = create_keystore(private_key, password, keystore_path)
    private_key = ""  # release the reference as early as Python permits

    contract = validate_contract_address(
        ask("NFT contract - WHAT: exact Robinhood Chain address; INPUT")
    )
    abi_path = str(
        Path(ask("ABI JSON path - WHAT: verified ABI file; INPUT")).expanduser().resolve()
    )
    abi = load_abi(abi_path)
    function = ask("Mint function - WHAT: exact ABI function; EXAMPLE: mint; INPUT")
    argument_text = typer.prompt(
        "Arguments JSON array - WHAT: legitimate quantity/proof/voucher values; DEFAULT: []",
        default="[]",
    )
    arguments = json.loads(argument_text)
    if not isinstance(arguments, list):
        raise typer.BadParameter("Arguments must be a JSON array")
    resolve_function(abi, function, len(arguments))
    quantity = int(ask("Quantity - DEFAULT/RECOMMENDED: 1", default="1"))
    value_eth = Decimal(ask("Exact transaction value in ETH - EXAMPLE: 0.05", default="0"))
    max_price = Decimal(
        ask("Hard max price per NFT in ETH", default=str(max(value_eth, Decimal("0.001"))))
    )
    max_fee = Decimal(ask("Hard max network fee in ETH", default="0.005"))
    max_total = Decimal(ask("Hard max total spend in ETH", default=str(value_eth + max_fee)))
    mode = ExecutionMode(ask("Mode: watch, confirm, or auto", default="watch").lower())
    if (
        mode == ExecutionMode.AUTO
        and ask("Type ENABLE AUTO to permit automatic broadcast") != "ENABLE AUTO"
    ):
        raise typer.Abort()
    telegram = TelegramSettings()
    if typer.confirm("Enable notification-only Telegram alerts?", default=False):
        token = getpass.getpass("Telegram bot token (hidden): ").strip()
        chat_id = ask("Telegram chat ID - notifications only; INPUT")
        asyncio.run(notify(token, chat_id, "Robinhood NFT Sniper: secure test notification"))
        telegram = TelegramSettings(enabled=True, bot_token=token, chat_id=chat_id)

    config = AppConfig(
        network=network_name,
        chain_id=network.chain_id,
        rpc=RPCSettings(
            primary=HttpUrl(primary),
            backups=[HttpUrl(item) for item in backups],
            websocket=websocket,
        ),
        wallet=WalletSettings(address=address, keystore_path=str(keystore_path)),
        target=TargetSettings(
            contract=contract,
            abi_path=abi_path,
            function=function,
            arguments=arguments,
            quantity=quantity,
            transaction_value_eth=value_eth,
        ),
        limits=LimitSettings(
            max_price_per_nft_eth=max_price,
            max_network_fee_eth=max_fee,
            max_total_spend_eth=max_total,
        ),
        mode=mode,
        telegram=telegram,
    )
    save_config(config)
    console.print(
        Panel(
            f"Saved securely\nNetwork: {network.name} ({network.chain_id})\n"
            f"Wallet: {abbreviated(address)}\nTarget: {abbreviated(contract)}\nMode: {mode}\n"
            "Next: robinhood-sniper doctor",
            title="Setup complete",
        )
    )


@app.command()
def launch() -> None:
    """Open the simple start/reconfigure menu."""
    try:
        config = load_config()
    except FileNotFoundError:
        easy_start()
        return
    action = choose(
        "Robinhood NFT Sniper",
        [
            "Start with the saved configuration",
            "Create a new numbered configuration",
            "Run safety checks and exit",
        ],
    )
    if action == 2:
        easy_start()
        return
    if action == 3:
        doctor()
        return
    console.print(
        Panel(
            f"Network: {config.network} ({config.chain_id})\n"
            f"Wallet: {abbreviated(config.wallet.address)}\n"
            f"Contract: {abbreviated(config.target.contract)}\n"
            f"Mode: {config.mode.value.upper()}",
            title="Saved configuration",
        )
    )
    if typer.confirm("Press Y to unlock and start", default=False):
        asyncio.run(_arm(False, False, None))


@app.command("easy-start")
def easy_start() -> None:
    """Numbered one-run setup that saves configuration and can arm immediately."""
    root = ensure_layout()
    console.print(
        Panel(
            "Choose numbers, paste only the requested values, then press Y to start.\n"
            "Your private key is hidden, encrypted locally, and never transmitted.",
            title="Robinhood Chain NFT Sniper - Easy Start",
        )
    )

    network_choice = choose(
        "1. Select the network",
        [
            "Robinhood Chain Testnet (recommended first run)",
            "Robinhood Chain Mainnet (real funds)",
        ],
    )
    network_name: Literal["testnet", "mainnet"] = "testnet" if network_choice == 1 else "mainnet"
    network = get_network(network_name)

    rpc_choice = choose(
        "2. Select RPC setup",
        [
            "Use Robinhood public RPC (easy; may be rate-limited)",
            "Use one custom HTTPS RPC (recommended for speed)",
            "Use a custom RPC plus backup RPCs (best reliability)",
        ],
    )
    if rpc_choice == 1:
        primary = network.public_rpc
        backups: list[str] = []
    else:
        primary = ask("Paste your Robinhood Chain HTTPS RPC link")
        backups = []
        if rpc_choice == 3:
            backup_text = typer.prompt(
                "Paste backup HTTPS RPC links separated by commas (maximum 5)", default=""
            ).strip()
            backups = [value.strip() for value in backup_text.split(",") if value.strip()]
            if len(backups) > 5:
                raise typer.BadParameter("A maximum of five backup RPCs is supported")
    console.print("Checking RPC chain ID and latency...")
    primary_latency = asyncio.run(validate_rpc(primary, network.chain_id))
    for url in backups:
        asyncio.run(validate_rpc(url, network.chain_id))
    console.print(f"[green]RPC ready: {primary_latency:.1f} ms[/green]")

    websocket_choice = choose(
        "3. WebSocket trigger",
        [
            "Skip WebSocket and use fast RPC/feed monitoring",
            "Paste a custom WebSocket RPC link (faster event wake-up)",
        ],
    )
    websocket: str | None = None
    if websocket_choice == 2:
        websocket = ask("Paste your wss:// Robinhood Chain WebSocket link")
        subscription = asyncio.run(probe_new_heads(websocket))
        console.print(f"[green]WebSocket ready: {abbreviated(subscription)}[/green]")

    console.print(
        Panel(
            "Use a brand-new, low-value mint wallet.\n"
            "Paste the key only into the hidden prompt below. It will not appear on screen.",
            title="4. Secure wallet",
        )
    )
    private_key = getpass.getpass("Private key (hidden): ").strip()
    password = getpass.getpass("Create a keystore password (12+ characters): ")
    if password != getpass.getpass("Repeat the keystore password: "):
        raise typer.BadParameter("The keystore passwords do not match")
    try:
        account = cast(LocalAccount, Account.from_key(private_key))
    except Exception as exc:
        raise typer.BadParameter("The private key is invalid") from exc
    keystore_path = root / "secrets" / "wallet.json"
    address = create_keystore(private_key, password, keystore_path)
    private_key = ""
    password = ""
    console.print(f"[green]Encrypted wallet ready: {abbreviated(address)}[/green]")

    console.print("\n[bold]5. NFT mint target[/bold]")
    target_choice = choose(
        "Select how to add the NFT",
        [
            "Paste an OpenSea NFT mint link (no contract or ABI needed)",
            "Paste the NFT contract and provide its verified ABI",
        ],
    )
    source: Literal["abi", "opensea"]
    abi_path: str | None = None
    function: str | None = None
    arguments: list[Any] = []
    opensea_slug: str | None = None
    opensea_url: str | None = None
    opensea_api_key_path: str | None = None
    suggested_quantity = "1"
    if target_choice == 1:
        if network_name != "mainnet":
            raise typer.BadParameter("OpenSea mint links require Robinhood Chain mainnet")
        source = "opensea"
        opensea_url = ask("Paste the OpenSea NFT mint link")
        try:
            opensea_slug = parse_opensea_mint_url(opensea_url)
            key_path = root / "secrets" / "opensea_api_key"

            async def resolve_drop() -> tuple[str, str]:
                client = OpenSeaClient(key_path)
                try:
                    drop = await client.get_drop(opensea_slug)
                    return drop.chain, drop.contract
                finally:
                    await client.close()

            drop_chain, contract = asyncio.run(resolve_drop())
        except OpenSeaError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if drop_chain != "robinhood":
            raise typer.BadParameter(
                f"That OpenSea drop is on '{drop_chain or 'an unknown chain'}', not Robinhood Chain"
            )
        opensea_api_key_path = str(key_path)
        console.print(
            f"[green]OpenSea drop verified: {opensea_slug} / {abbreviated(contract)}[/green]"
        )
    else:
        source = "abi"
        contract = validate_contract_address(ask("Paste the NFT contract address"))
        abi_choice = choose(
            "Select how to provide the verified ABI",
            [
                "Paste a direct HTTPS ABI/explorer API link",
                "Enter the path to an ABI JSON file already on this VPS",
            ],
        )
        if abi_choice == 1:
            abi_url = ask("Paste the direct HTTPS ABI JSON link")
            abi_path_obj = root / "target" / "abi.json"
            try:
                asyncio.run(download_abi(abi_url, abi_path_obj))
            except Exception as exc:
                raise typer.BadParameter(redact(exc)) from exc
        else:
            abi_path_obj = Path(ask("Enter the ABI JSON file path")).expanduser().resolve()
        abi_path = str(abi_path_obj)
        abi = load_abi(abi_path)
        candidates = mint_candidates(abi)
        if not candidates:
            raise typer.BadParameter("The ABI contains no payable/nonpayable mint functions")
        function_choice = choose(
            "Select the exact mint function",
            [function_signature(item) for item in candidates],
        )
        selected_function = candidates[function_choice - 1]
        function = str(selected_function["name"])
        inputs = selected_function.get("inputs", [])
        for index, item in enumerate(inputs, start=1):
            type_name = str(item.get("type", "string"))
            input_name = str(item.get("name") or f"argument_{index}")
            while True:
                raw_value = ask(f"Enter {input_name} ({type_name})")
                try:
                    arguments.append(parse_abi_input(type_name, raw_value))
                    break
                except SetupInputError as exc:
                    console.print(f"[yellow]{exc}[/yellow]")
        resolve_function(abi, function, len(arguments))
        for item, value in zip(inputs, arguments, strict=True):
            name = str(item.get("name", "")).lower()
            if name in {"quantity", "amount", "count", "qty"} and isinstance(value, int):
                suggested_quantity = str(value)
                break

    quantity = int(ask("NFT quantity for the safety limits", default=suggested_quantity))
    value_eth = (
        Decimal(ask("Exact total ETH value sent to the mint", default="0"))
        if source == "abi"
        else Decimal("0")
    )

    console.print("\n[bold]6. Hard spending limits[/bold]")
    max_price = Decimal(ask("Maximum price per NFT in ETH", default="0.001"))
    max_fee = Decimal(ask("Maximum network fee in ETH", default="0.005"))
    suggested_total = max(value_eth, max_price * quantity) + max_fee
    max_total = Decimal(ask("Maximum total spend in ETH", default=str(suggested_total)))

    mode_choice = choose(
        "7. Select execution mode",
        [
            "WATCH - check and report only; never broadcast",
            "CONFIRM - ask once more when the mint opens",
            "AUTO - broadcast automatically after every safety check passes",
        ],
    )
    mode = (ExecutionMode.WATCH, ExecutionMode.CONFIRM, ExecutionMode.AUTO)[mode_choice - 1]

    telegram = TelegramSettings()
    telegram_choice = choose(
        "8. Telegram notifications",
        ["No Telegram", "Enable notification-only Telegram"],
    )
    if telegram_choice == 2:
        token = getpass.getpass("Telegram bot token (hidden): ").strip()
        chat_id = ask("Telegram chat ID")
        asyncio.run(notify(token, chat_id, "Robinhood NFT Sniper: setup test successful"))
        telegram = TelegramSettings(enabled=True, bot_token=token, chat_id=chat_id)

    config = AppConfig(
        network=network_name,
        chain_id=network.chain_id,
        rpc=RPCSettings(
            primary=HttpUrl(primary),
            backups=[HttpUrl(item) for item in backups],
            websocket=websocket,
        ),
        wallet=WalletSettings(address=address, keystore_path=str(keystore_path)),
        target=TargetSettings(
            name=(
                f"OpenSea {opensea_slug} mint" if source == "opensea" else f"{function} NFT mint"
            ),
            source=source,
            contract=contract,
            abi_path=abi_path,
            function=function,
            arguments=arguments,
            opensea_slug=opensea_slug,
            opensea_url=opensea_url,
            opensea_api_key_path=opensea_api_key_path,
            quantity=quantity,
            transaction_value_eth=value_eth,
        ),
        limits=LimitSettings(
            max_price_per_nft_eth=max_price,
            max_network_fee_eth=max_fee,
            max_total_spend_eth=max_total,
        ),
        mode=mode,
        telegram=telegram,
    )
    save_config(config)

    mint_value_summary = (
        "from OpenSea, limited below" if source == "opensea" else f"{value_eth} ETH"
    )
    console.print(
        Panel(
            f"Network: {network.name} ({network.chain_id})\n"
            f"Wallet: {abbreviated(address)}\n"
            f"Contract: {abbreviated(contract)}\n"
            f"Target: {opensea_slug if source == 'opensea' else function}\nQuantity: {quantity}\n"
            f"Mint value: {mint_value_summary}\n"
            f"Max fee: {max_fee} ETH\n"
            f"Max total: {max_total} ETH\nMode: {mode.value.upper()}\n"
            "The key is encrypted locally. Final simulation and limits remain mandatory.",
            title="Ready to start",
        )
    )
    if not typer.confirm("Press Y to start the bot now", default=False):
        console.print("Configuration saved. Start later with: bash start.sh")
        return
    asyncio.run(_arm(False, False, None, unlocked_account=account))


def _unlock(config: AppConfig) -> LocalAccount:
    password = None
    if not os.getenv("ROBINHOOD_SNIPER_PRIVATE_KEY"):
        password = getpass.getpass("Keystore password: ")
    account = load_local_account(Path(config.wallet.keystore_path), password)
    if account.address.lower() != config.wallet.address.lower():
        raise RuntimeError("Unlocked wallet does not match configured wallet")
    return account


async def _doctor() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    try:
        config = load_config()
        checks.append(("config", True, f"{config.network} / {config.chain_id}"))
    except Exception as exc:
        return [("config", False, str(exc))]
    checks.append(
        ("python", platform.python_version_tuple() >= ("3", "12", "0"), platform.python_version())
    )
    pool = RPCPool(config.rpc.all_http(), config.chain_id, config.rpc.timeout_seconds)
    try:
        health = await pool.validate()
        checks.append(("RPC", True, f"{len(health)} endpoint(s) healthy"))
        code = await pool.call("eth_getCode", [config.target.contract, "latest"])
        checks.append(("contract", code not in {"0x", "0x0"}, f"{(len(code) - 2) // 2} byte(s)"))
        balance = int(await pool.call("eth_getBalance", [config.wallet.address, "latest"]), 16)
        checks.append(("wallet balance", balance > 0, f"{balance / 10**18:.6f} ETH"))
    except Exception as exc:
        checks.append(("RPC/network", False, redact(exc)))
    finally:
        await pool.close()
    if config.rpc.websocket:
        try:
            subscription = await probe_new_heads(config.rpc.websocket)
            checks.append(("WebSocket newHeads", True, abbreviated(subscription)))
        except Exception as exc:
            checks.append(("WebSocket newHeads", False, redact(exc)))
    if config.target.source == "opensea":
        try:
            assert config.target.opensea_api_key_path is not None
            assert config.target.opensea_slug is not None
            client = OpenSeaClient(Path(config.target.opensea_api_key_path))
            try:
                drop = await client.get_drop(config.target.opensea_slug)
            finally:
                await client.close()
            checks.append(
                (
                    "OpenSea drop",
                    drop.chain == "robinhood"
                    and drop.contract.lower() == config.target.contract.lower(),
                    f"{drop.slug} / {drop.chain}",
                )
            )
        except Exception as exc:
            checks.append(("OpenSea drop", False, redact(exc)))
    else:
        try:
            assert config.target.abi_path is not None
            assert config.target.function is not None
            resolve_function(
                load_abi(config.target.abi_path),
                config.target.function,
                len(config.target.arguments),
            )
            checks.append(("ABI/function", True, config.target.function))
        except Exception as exc:
            checks.append(("ABI/function", False, str(exc)))
    for finding in audit_permissions():
        checks.append((finding.name, finding.ok, finding.detail))
    if shutil.which("timedatectl"):
        executable = shutil.which("timedatectl")
        assert executable is not None
        process = await asyncio.create_subprocess_exec(
            executable,
            "show",
            "-p",
            "NTPSynchronized",
            "--value",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()
        clock_status = stdout.decode().strip()
        synchronized = clock_status.lower() == "yes"
        checks.append(("clock sync", synchronized, clock_status or "unknown"))
    StateStore()
    checks.append(("SQLite state", True, "ready; no secrets stored"))
    return checks


@app.command()
def doctor() -> None:
    """Check whether the system is safe and ready to arm."""
    checks = asyncio.run(_doctor())
    table = Table("Check", "Result", "Detail")
    for name, ok, detail in checks:
        table.add_row(name, "PASS" if ok else "FAIL", detail)
    console.print(table)
    if not all(item[1] for item in checks):
        console.print("[red]NOT READY[/red]")
        raise typer.Exit(1)
    console.print("[green]READY[/green]")


async def _benchmark(rounds: int) -> None:
    config = load_config()
    pool = RPCPool(config.rpc.all_http(), config.chain_id, config.rpc.timeout_seconds)
    try:
        health = await pool.benchmark(rounds)
    finally:
        await pool.close()
    table = Table("RPC", "Latency", "Reliability", "Block", "Status")
    for item in health:
        table.add_row(
            redact(item.url),
            f"{item.latency_ms:.1f} ms",
            f"{item.reliability:.0%}",
            str(item.block_number),
            item.last_error or "healthy",
        )
    console.print(table)


@app.command()
def benchmark(rounds: Annotated[int, typer.Option(min=1, max=20)] = 5) -> None:
    """Read-only configured-RPC latency, freshness and reliability test."""
    asyncio.run(_benchmark(rounds))


async def _arm(
    dry_run: bool,
    rearm: bool,
    watch_timeout: float | None,
    unlocked_account: LocalAccount | None = None,
) -> None:
    config = load_config()
    account = unlocked_account or _unlock(config)
    engine = MintEngine(config, account, StateStore())
    try:
        prepared = await engine.prepare(allow_rearm=rearm)
        console.print(
            Panel(
                f"Network: {config.network} ({config.chain_id})\n"
                f"Wallet: {abbreviated(account.address)}\n"
                f"Target: {config.target.name} / {abbreviated(config.target.contract)}\n"
                f"Mode: {'dry-run' if dry_run else config.mode}\n"
                f"RPCs ready: {len(cast(Sized, prepared['rpc']))}\n"
                "Waiting for successful final simulation...",
                title="ARMED",
            )
        )
        if config.telegram.enabled and config.telegram.bot_token and config.telegram.chat_id:
            try:
                await notify(
                    config.telegram.bot_token,
                    config.telegram.chat_id,
                    f"Robinhood NFT Sniper ARMED on {config.network}: "
                    f"{abbreviated(config.target.contract)}",
                )
            except Exception as exc:
                console.print(f"[yellow]Telegram warning: {redact(exc)}[/yellow]")
        await engine.wait_for_trigger(watch_timeout)
        confirmed = False
        if config.mode == ExecutionMode.CONFIRM and not dry_run:
            confirmed = typer.confirm("Simulation succeeds. Broadcast now?", default=False)
        result = await engine.execute(dry_run=dry_run, confirmed=confirmed)
        if config.telegram.enabled and config.telegram.bot_token and config.telegram.chat_id:
            try:
                await notify(
                    config.telegram.bot_token,
                    config.telegram.chat_id,
                    f"Robinhood NFT Sniper result: {result.state}; "
                    f"tx {abbreviated(result.tx_hash) if result.tx_hash else 'none'}",
                )
            except Exception as exc:
                console.print(f"[yellow]Telegram warning: {redact(exc)}[/yellow]")
        console.print(
            Panel(
                f"State: {result.state}\nMessage: {result.message or 'complete'}\n"
                f"Transaction: {abbreviated(result.tx_hash) if result.tx_hash else 'none'}\n"
                f"Timings: {json.dumps(result.timings_ms, indent=2)}",
                title="NFT SNIPER RESULT",
            )
        )
    finally:
        await engine.close()


@app.command()
def arm(
    dry_run: Annotated[
        bool, typer.Option(help="Simulate and check limits; never sign/broadcast")
    ] = False,
    rearm: Annotated[
        bool, typer.Option(help="Explicitly allow another run for this wallet/target")
    ] = False,
    watch_timeout: Annotated[
        float | None, typer.Option(help="Optional seconds before stopping the watcher")
    ] = None,
) -> None:
    """Preload, validate, monitor, simulate and execute according to mode."""
    if rearm and not typer.confirm("Rearm can mint again. Continue?", default=False):
        raise typer.Abort()
    asyncio.run(_arm(dry_run, rearm, watch_timeout))


@app.command("dry-run")
def dry_run(watch_timeout: float | None = None) -> None:
    """Alias for `arm --dry-run`."""
    asyncio.run(_arm(True, False, watch_timeout))


@app.command("security-check")
def security_check() -> None:
    """Audit local permissions and key-storage exposure."""
    table = Table("Check", "Result", "Detail")
    failed = False
    for finding in audit_permissions():
        table.add_row(finding.name, "PASS" if finding.ok else "FAIL", finding.detail)
        failed |= not finding.ok
    console.print(table)
    if failed:
        raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Print persisted states and real measured hot-path timings."""
    table = Table("Run", "State", "Wallet", "Contract", "Tx", "Timings (ms)")
    for row in StateStore().last_runs():
        table.add_row(
            str(row["id"]),
            row["state"],
            abbreviated(row["wallet"]),
            abbreviated(row["contract"]),
            abbreviated(row["tx_hash"] or "none"),
            row["timings_json"],
        )
    console.print(table)


@app.command()
def profile(iterations: Annotated[int, typer.Option(min=10, max=10_000)] = 500) -> None:
    """Measure local ABI encoding only; does not broadcast."""
    config = load_config()
    if config.target.source == "opensea":
        console.print("OpenSea targets receive calldata from the official API at mint time.")
        raise typer.Exit(0)
    assert config.target.abi_path is not None
    assert config.target.function is not None
    abi = load_abi(config.target.abi_path)
    samples = []
    from sniper.contract.analyzer import encode_call

    for _ in range(iterations):
        started = time.perf_counter_ns()
        encode_call(config.target.contract, abi, config.target.function, config.target.arguments)
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    console.print(
        f"ABI encoding: median {statistics.median(samples):.4f} ms, "
        f"p95 {sorted(samples)[int(len(samples) * 0.95) - 1]:.4f} ms ({iterations} real runs)"
    )


@config_app.command("show")
def config_show() -> None:
    """Show sanitized configuration."""
    payload = load_config().model_dump(mode="json")
    if payload.get("telegram", {}).get("bot_token"):
        payload["telegram"]["bot_token"] = "[REDACTED]"  # noqa: S105
    payload["rpc"]["primary"] = redact(payload["rpc"]["primary"])
    payload["rpc"]["backups"] = [redact(item) for item in payload["rpc"]["backups"]]
    console.print_json(data=payload)


@config_app.command("rpc")
def config_rpc() -> None:
    """Replace configured RPCs through prompts so credentials avoid shell history."""
    config = load_config()
    primary = ask("New primary HTTPS RPC")
    asyncio.run(validate_rpc(primary, config.chain_id))
    backup_text = typer.prompt("Backup RPCs, comma-separated; blank for none", default="").strip()
    backups = [item.strip() for item in backup_text.split(",") if item.strip()]
    for url in backups:
        asyncio.run(validate_rpc(url, config.chain_id))
    websocket = typer.prompt("WebSocket RPC; blank to disable", default="").strip() or None
    if websocket:
        asyncio.run(probe_new_heads(websocket))
    rpc = RPCSettings(
        primary=HttpUrl(primary),
        backups=[HttpUrl(item) for item in backups],
        websocket=websocket,
        timeout_seconds=config.rpc.timeout_seconds,
    )
    save_config(config.model_copy(update={"rpc": rpc}))
    console.print("RPC configuration validated and saved.")


@config_app.command("limits")
def config_limits() -> None:
    """Replace all three hard spending limits together."""
    config = load_config()
    limits = LimitSettings(
        max_price_per_nft_eth=Decimal(ask("Max price per NFT in ETH")),
        max_network_fee_eth=Decimal(ask("Max network fee in ETH")),
        max_total_spend_eth=Decimal(ask("Max total spend in ETH")),
        balance_buffer_eth=Decimal(
            ask("Balance buffer in ETH", default=str(config.limits.balance_buffer_eth))
        ),
    )
    save_config(config.model_copy(update={"limits": limits}))
    console.print("Hard limits saved. Run doctor and dry-run.")


@config_app.command("telegram")
def config_telegram() -> None:
    """Configure notification-only Telegram; token entry is hidden."""
    config = load_config()
    if not typer.confirm("Enable Telegram notifications?", default=False):
        save_config(config.model_copy(update={"telegram": TelegramSettings()}))
        console.print("Telegram disabled.")
        return
    token = getpass.getpass("Telegram bot token (hidden): ").strip()
    chat_id = ask("Telegram chat ID")
    asyncio.run(notify(token, chat_id, "Robinhood NFT Sniper: secure test notification"))
    save_config(
        config.model_copy(
            update={"telegram": TelegramSettings(enabled=True, bot_token=token, chat_id=chat_id)}
        )
    )
    console.print("Notification-only Telegram saved.")


@wallet_app.command("status")
def wallet_status() -> None:
    config = load_config()
    path = Path(config.wallet.keystore_path)
    console.print(
        f"Address: {abbreviated(config.wallet.address)}\nEncrypted keystore: {path.exists()}\n"
        f"File mode: {oct(path.stat().st_mode & 0o777) if path.exists() else 'missing'}"
    )


@wallet_app.command("replace")
def wallet_replace() -> None:
    config = load_config()
    console.print("Use another dedicated, low-value wallet. Existing key will be overwritten.")
    private_key = getpass.getpass("New private key: ")
    password = getpass.getpass("New keystore password (12+ chars): ")
    if password != getpass.getpass("Repeat password: "):
        raise typer.BadParameter("Passwords do not match")
    path = Path(config.wallet.keystore_path)
    address = create_keystore(private_key, password, path)
    private_key = ""
    updated = config.model_copy(
        update={"wallet": WalletSettings(address=address, keystore_path=str(path))}
    )
    save_config(updated)
    console.print(f"Wallet replaced: {abbreviated(address)}")


@target_app.command("set")
def target_set(
    contract: str,
    abi_path: Path,
    function: str,
    arguments_json: str = "[]",
    quantity: int = 1,
    value_eth: str = "0",
) -> None:
    config = load_config()
    arguments = json.loads(arguments_json)
    if not isinstance(arguments, list):
        raise typer.BadParameter("arguments-json must be a JSON array")
    address = validate_contract_address(contract)
    abi = load_abi(str(abi_path))
    resolve_function(abi, function, len(arguments))
    target = TargetSettings(
        contract=address,
        abi_path=str(abi_path.resolve()),
        function=function,
        arguments=arguments,
        quantity=quantity,
        transaction_value_eth=Decimal(value_eth),
    )
    save_config(config.model_copy(update={"target": target}))
    console.print("Target saved. Run doctor and dry-run before arming.")


@service_app.command("install")
def service_install() -> None:
    console.print(f"Installed {install_unit()}")


for _action in ("start", "stop", "restart", "status"):
    service_app.command(_action)(lambda action=_action: systemctl(action))


if __name__ == "__main__":
    app()
