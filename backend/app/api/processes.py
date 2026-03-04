"""
Process management API + system info.
Guarded by the 'system_access_enabled' system setting.
"""
import os
import platform
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.api.settings import get_setting_value

router = APIRouter(prefix="/api/processes", tags=["processes"])


# ---------- Guard ----------
async def _check_system_access(db: AsyncSession):
    val = await get_setting_value(db, "system_access_enabled")
    if val != "true":
        raise HTTPException(
            status_code=403,
            detail="System access is disabled. Enable it in Settings → System.",
        )


# ---------- Schemas ----------
class KillRequest(BaseModel):
    pid: int
    signal: int = 15  # SIGTERM


# ---------- Helper ----------
def _get_process_list() -> list[dict]:
    """Cross-platform process list using psutil if available, else /bin/ps."""
    try:
        import psutil
        processes = []
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'username', 'status',
                                          'cpu_percent', 'memory_percent',
                                          'create_time', 'cmdline']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "ppid": info.get('ppid', 0),
                    "name": info.get('name', ''),
                    "username": info.get('username', ''),
                    "status": info.get('status', ''),
                    "cpu_percent": round(info.get('cpu_percent', 0) or 0, 1),
                    "memory_percent": round(info.get('memory_percent', 0) or 0, 1),
                    "created": datetime.fromtimestamp(info['create_time']).isoformat()
                    if info.get('create_time') else None,
                    "command": ' '.join(info.get('cmdline') or [])[:200],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return processes
    except ImportError:
        pass

    # Fallback: use subprocess
    import subprocess
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=10,
        )
        processes = []
        for line in result.stdout.strip().split("\n")[1:]:  # skip header
            parts = line.split(None, 10)
            if len(parts) >= 11:
                processes.append({
                    "pid": int(parts[1]),
                    "ppid": 0,
                    "name": parts[10].split()[0].split("/")[-1] if parts[10] else "",
                    "username": parts[0],
                    "status": parts[7] if len(parts) > 7 else "",
                    "cpu_percent": float(parts[2]),
                    "memory_percent": float(parts[3]),
                    "created": None,
                    "command": parts[10][:200],
                })
        return processes
    except Exception:
        return []


def _get_system_info() -> dict:
    """Gather system information."""
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }

    try:
        import psutil
        # CPU
        info["cpu_count"] = psutil.cpu_count()
        info["cpu_count_logical"] = psutil.cpu_count(logical=True)
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            info["cpu_freq_mhz"] = round(cpu_freq.current, 0)

        # Memory
        mem = psutil.virtual_memory()
        info["memory_total"] = mem.total
        info["memory_available"] = mem.available
        info["memory_used"] = mem.used
        info["memory_percent"] = mem.percent

        # Swap
        swap = psutil.swap_memory()
        info["swap_total"] = swap.total
        info["swap_used"] = swap.used
        info["swap_percent"] = swap.percent

        # Disk
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                })
            except PermissionError:
                continue
        info["disks"] = disks

        # Network
        net = psutil.net_io_counters()
        info["network"] = {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        }

        # Boot time
        info["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
        info["uptime_seconds"] = int(time.time() - psutil.boot_time())

    except ImportError:
        info["note"] = "Install 'psutil' for detailed system info"

        # Basic fallback
        import subprocess
        try:
            result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info["memory_total"] = int(result.stdout.strip())
        except Exception:
            pass

    return info


# ---------- Endpoints ----------

@router.get("/list")
async def list_processes(
    sort_by: str = Query("cpu_percent", description="Sort field"),
    sort_desc: bool = Query(True),
    filter_name: str = Query(None, description="Filter by process name"),
    limit: int = Query(100, le=500),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List running processes."""
    await _check_system_access(db)

    processes = _get_process_list()

    # Filter
    if filter_name:
        fl = filter_name.lower()
        processes = [p for p in processes if fl in p.get("name", "").lower()
                     or fl in p.get("command", "").lower()]

    # Sort
    try:
        processes.sort(key=lambda p: p.get(sort_by, 0) or 0, reverse=sort_desc)
    except (KeyError, TypeError):
        pass

    return {
        "processes": processes[:limit],
        "total": len(processes),
    }


@router.post("/kill")
async def kill_process(
    body: KillRequest,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a signal to a process."""
    await _check_system_access(db)

    import signal as sig

    # Validate signal
    allowed_signals = {
        2: "SIGINT",
        9: "SIGKILL",
        15: "SIGTERM",
        18: "SIGCONT",
        19: "SIGSTOP",
    }
    if body.signal not in allowed_signals:
        raise HTTPException(
            status_code=400,
            detail=f"Signal {body.signal} not allowed. Use one of: {allowed_signals}",
        )

    try:
        os.kill(body.pid, body.signal)
    except ProcessLookupError:
        raise HTTPException(status_code=404, detail=f"Process {body.pid} not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied to signal PID {body.pid}")

    return {
        "pid": body.pid,
        "signal": body.signal,
        "signal_name": allowed_signals[body.signal],
        "message": f"Signal {allowed_signals[body.signal]} sent to PID {body.pid}",
    }


@router.get("/system-info")
async def system_info(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get system information (CPU, RAM, disk, network)."""
    await _check_system_access(db)
    return _get_system_info()


@router.get("/{pid}")
async def get_process_detail(
    pid: int,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info about a specific process."""
    await _check_system_access(db)

    try:
        import psutil
        proc = psutil.Process(pid)
        with proc.oneshot():
            info = {
                "pid": proc.pid,
                "ppid": proc.ppid(),
                "name": proc.name(),
                "username": proc.username(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": round(proc.memory_percent(), 2),
                "memory_rss": proc.memory_info().rss,
                "memory_vms": proc.memory_info().vms,
                "created": datetime.fromtimestamp(proc.create_time()).isoformat(),
                "command": ' '.join(proc.cmdline()),
                "cwd": proc.cwd(),
                "num_threads": proc.num_threads(),
                "nice": proc.nice(),
            }
            try:
                info["open_files"] = [f.path for f in proc.open_files()]
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info["open_files"] = []
            try:
                conns = proc.connections()
                info["connections"] = [
                    {"fd": c.fd, "family": str(c.family), "type": str(c.type),
                     "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                     "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                     "status": c.status}
                    for c in conns
                ]
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info["connections"] = []
            return info
    except ImportError:
        raise HTTPException(status_code=501, detail="psutil not installed — cannot get process detail")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
