from pathlib import Path
import shadowcopy.shadow as shadow  # type: ignore[reportMissingTypeStubs]
from utils.utils import code_logger


def is_readable(path: Path) -> bool:
    try:
        with open(path, 'rb'):
            return True
    except Exception as e:
        code_logger.warning(f"Source file may be locked or unreadable: {e}")
        return False


def create_shadow_copy(src_path: Path, dest_path: Path):
    code_logger.info(f"Creating shadow copy from {src_path} to {dest_path}")
    shadow.shadow_copy(str(src_path), str(dest_path))
    code_logger.info("Shadow copy created successfully.")
    code_logger.info(f"Shadow file size: {dest_path.stat().st_size} bytes")


def main():
    brave_user_data = Path.home() / r"AppData\Local\BraveSoftware\Brave-Browser\User Data"
    cookie_src = brave_user_data / r"Default\Network\Cookies"
    state_src = brave_user_data / "Local State"

    dest_folder = Path(__file__).parent / "data" / "config"
    dest_folder.mkdir(parents=True, exist_ok=True)

    cookie_dest = dest_folder / "Cookies"
    state_dest = dest_folder / "Local State"

    try:
        if not cookie_src.exists():
            code_logger.error(f"Brave cookies not found: {cookie_src}")
            return
        if not state_src.exists():
            code_logger.error(f"Local State not found: {state_src}")
            return

        create_shadow_copy(cookie_src, cookie_dest)
        create_shadow_copy(state_src, state_dest)

    except PermissionError:
        code_logger.error("Permission denied. Run as Administrator.")
    except Exception as e:
        code_logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
