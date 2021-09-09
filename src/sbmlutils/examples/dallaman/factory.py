"""DallMan model factory."""
from pathlib import Path
from sbmlutils.factory import create_model
from sbmlutils.examples.dallaman.model import dallaman_model


def create(tmp: bool = False) -> None:
    """Create model."""
    create_model(
        create_model = dallaman_model,
        output_dir=Path(__file__).parent / "results",
        tmp=tmp,
        units_consistency=False,
    )


if __name__ == "__main__":
    create()
