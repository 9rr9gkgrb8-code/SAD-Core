"""Generate Personal Study output through an explicitly configured local model."""

from model_adapter import generate_local_response


def generate_study_result(request, plan, display_name):
    """Return model output when available and an honest useful fallback otherwise."""
    prompt = (
        "Personal Study request\n"
        f"Action: {request.action.value}\nCourse: {request.course or 'unspecified'}\n"
        f"Depth: {request.requested_depth}\nInstruction: {plan.instruction}\n"
        f"Boundaries: {'; '.join(plan.boundaries)}\nMaterial:\n{request.material}"
    )
    generated = generate_local_response(prompt, display_name, [])
    if generated:
        return {"status": "generated", "content": generated, "provider": "local_model"}
    return {
        "status": "model_unavailable",
        "content": (
            "Your study request is ready, but no approved local model is configured. "
            "Configure SAD_LOCAL_MODEL and start its loopback-only service to generate the full response."
        ),
        "provider": None,
    }
