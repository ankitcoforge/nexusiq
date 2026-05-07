from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel
from datetime import datetime

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class FraudFlagSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    UNAVAILABLE = "unavailable"
    MANUAL_REVIEW = "manual_review"

class VerdictType(str, Enum):
    APPROVE = "Approve for Processing"
    APPROVE_WITH_NOTATION = "Approve with Notation"
    ESCALATE_SIU = "Escalate to SIU"

class ExtractedField(BaseModel):
    value: str = ""
    confidence: float = 0.0
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

class VendorInfo(BaseModel):
    name: ExtractedField = ExtractedField()
    address: ExtractedField = ExtractedField()
    phone: ExtractedField = ExtractedField()
    website: ExtractedField = ExtractedField()

class CustomerInfo(BaseModel):
    name: ExtractedField = ExtractedField()
    address: ExtractedField = ExtractedField()
    phone: ExtractedField = ExtractedField()

class VehicleInfo(BaseModel):
    make: ExtractedField = ExtractedField()
    model: ExtractedField = ExtractedField()
    year: ExtractedField = ExtractedField()
    vin: ExtractedField = ExtractedField()
    mileage: ExtractedField = ExtractedField()

class LineItem(BaseModel):
    description: str = ""
    part_number: Optional[str] = None
    quantity: float = 0.0
    unit_price: float = 0.0
    total: float = 0.0
    is_taxable: bool = True
    confidence: float = 0.0

class InvoiceData(BaseModel):
    invoice_number: ExtractedField = ExtractedField()
    invoice_date: ExtractedField = ExtractedField()
    vendor: VendorInfo = VendorInfo()
    customer: CustomerInfo = CustomerInfo()
    vehicle: VehicleInfo = VehicleInfo()
    line_items: List[LineItem] = []
    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    raw_text: str = ""

class FraudFlag(BaseModel):
    check_name: str
    severity: FraudFlagSeverity
    message: str
    details: str = ""

class VerificationStepResult(BaseModel):
    step_number: int
    step_name: str
    status: CheckStatus = CheckStatus.PASSED
    summary: str = ""
    details: str = ""
    thought_process: str = ""
    flags: List[FraudFlag] = []
    duration_seconds: float = 0.0

class ArithmeticCheckResult(VerificationStepResult):
    line_item_checks: List[dict] = []
    computed_subtotal: float = 0.0
    computed_tax: float = 0.0
    computed_total: float = 0.0
    invoice_total: float = 0.0

class VendorCheckResult(VerificationStepResult):
    vendor_found: bool = False
    official_phone: str = ""
    official_address: str = ""
    search_sources: List[str] = []

class PriceCheckResult(VerificationStepResult):
    price_comparisons: List[dict] = []

class VINCheckResult(VerificationStepResult):
    vin_valid: bool = False
    decoded_year: str = ""
    decoded_make: str = ""
    decoded_model: str = ""

class FraudReport(BaseModel):
    session_id: str
    document_name: str
    analysis_date: str
    invoice_data: InvoiceData
    verification_results: List[VerificationStepResult] = []
    total_flags: int = 0
    critical_flags: int = 0
    verdict: VerdictType = VerdictType.APPROVE
    verdict_reasoning: str = ""
    recommendation: str = ""

class ChatMessage(BaseModel):
    role: str
    content: str
    message_type: str = "text"
    data: Optional[Any] = None
    timestamp: str = ""

class UploadResponse(BaseModel):
    session_id: str
    file_name: str
    message: str
    status: str = "uploaded"

class SessionData(BaseModel):
    session_id: str
    file_bytes: Optional[bytes] = None
    file_name: str = ""
    status: str = "init"
    invoice_data: Optional[InvoiceData] = None
    fraud_report: Optional[FraudReport] = None
    chat_history: List[ChatMessage] = []
    
    model_config = {"arbitrary_types_allowed": True}
