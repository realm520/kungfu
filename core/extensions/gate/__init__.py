from .md import MarketDataGate
from .td import TraderGate
from extensions import EXTENSION_REGISTRY_MD, EXTENSION_REGISTRY_TD
EXTENSION_REGISTRY_MD.register_extension('gate', MarketDataXT)
EXTENSION_REGISTRY_TD.register_extension('gate', TraderXT)
