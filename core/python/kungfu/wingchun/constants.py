
import pywingchun

class Source:
    CTP = "ctp"
    SIM = "sim"
    XT = 'xt'
    RESTBN = "restbn"

class Exchange:
    SSE = "SSE"
    SZE = "SZE"
    SHFE = "SHFE"
    XT = 'XT'
    BN = "bn"

class Region:
    CN = 'CN'
    HK = 'HK'

InstrumentType = pywingchun.constants.InstrumentType
ExecType = pywingchun.constants.ExecType
Side = pywingchun.constants.Side
Offset = pywingchun.constants.Offset
BsFlag = pywingchun.constants.BsFlag
OrderStatus = pywingchun.constants.OrderStatus
Direction = pywingchun.constants.Direction
PriceType = pywingchun.constants.PriceType
VolumeCondition = pywingchun.constants.VolumeCondition
TimeCondition = pywingchun.constants.TimeCondition
OrderActionFlag = pywingchun.constants.OrderActionFlag
LedgerCategory = pywingchun.constants.LedgerCategory
HedgeFlag = pywingchun.constants.HedgeFlag

AllFinalOrderStatus = [OrderStatus.Filled, OrderStatus.Error, OrderStatus.PartialFilledNotActive, OrderStatus.Cancelled]

InstrumentTypeInStockAccount = [InstrumentType.Stock,
                                InstrumentType.Bond,
                                InstrumentType.Fund,
                                InstrumentType.Spot,
                                InstrumentType.Index,
                                InstrumentType.Repo]

ENUM_TYPES = [InstrumentType,
              ExecType,
              Side,
              Offset,
              BsFlag,
              OrderStatus,
              Direction,
              PriceType,
              VolumeCondition,
              TimeCondition,
              OrderActionFlag,
              LedgerCategory,
              HedgeFlag]
