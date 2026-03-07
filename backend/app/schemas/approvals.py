from pydantic import BaseModel, model_validator


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

    @model_validator(mode="after")
    def validate_png_signature(self):
        if not self.signature_object_path.lower().endswith(".png"):
            raise ValueError("signature_object_path must be a .png")
        return self


class CustomerSignOut(BaseModel):
    status: str
    final_report_pdf_url: str | None
