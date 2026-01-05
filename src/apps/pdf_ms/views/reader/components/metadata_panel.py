from src.apps.pdf_ms.views.metadata_view import MetadataView

class MetadataPanel(MetadataView):
    """
    Modular Right Panel for PDF Reader.
    Wraps existing MetadataView for consistency in Reader V2 architecture.
    """
    def __init__(self):
        super().__init__()
        # We can add reader-specific customizations here if needed
