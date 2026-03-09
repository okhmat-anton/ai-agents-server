# Image analysis using vision-capable LLM.
# Primary execution path is via the pipeline handler (_sys_image_analyze).

async def execute(image_url, question="Describe this image in detail"):
    """Analyze an image using vision LLM. Requires pipeline context for LLM access."""
    return {
        "error": "image_analyze requires a vision-capable LLM accessed through the pipeline. "
                 "This skill must be executed through the pipeline handler."
    }
