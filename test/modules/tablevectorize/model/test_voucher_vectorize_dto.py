from pathlib import Path
import sys


def _prepare_src_import_path() -> None:
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_prepare_src_import_path()

from modules.table_vectorize.model.dto.voucher_vectorize_dto import VoucherVectorizeDto


def test_voucher_vectorize_dto_shop_name_is_string() -> None:
    assert VoucherVectorizeDto.model_fields["shop_name"].annotation is str
