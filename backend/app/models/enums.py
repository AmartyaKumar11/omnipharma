import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    BRANCH_MANAGER = "BRANCH_MANAGER"
    INVENTORY_CONTROLLER = "INVENTORY_CONTROLLER"
    STAFF = "STAFF"


class InventoryChangeType(str, enum.Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    ADJUST = "ADJUST"


class InventoryLogSourceType(str, enum.Enum):
    SALE = "SALE"
    RESTOCK = "RESTOCK"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"


class AlertType(str, enum.Enum):
    LOW_STOCK = "LOW_STOCK"
    EXPIRY = "EXPIRY"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class OrderType(str, enum.Enum):
    OTC = "OTC"
    PRESCRIPTION = "PRESCRIPTION"


class OrderStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"
    UPI = "UPI"


class PrescriptionStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
