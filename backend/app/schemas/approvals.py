from pydantic import BaseModel


class ApprovalViewOut(BaseModel):
    workorder_id: str
    site_name: str
    scheduled_at: str
    visit_status: str | None
    summary: dict
    report_pdf_url: str | None
    sign_required: bool


class CustomerSignIn(BaseModel):
    signer_name: str
    signer_phone: str
    signature_object_path: str


class CustomerSignOut(BaseModel):
    status: str
    final_report_pdf_url: str | None