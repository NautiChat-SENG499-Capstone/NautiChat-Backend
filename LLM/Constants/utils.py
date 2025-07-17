def sync_param(field_name: str, local_value, params_model, allObtainedParams: dict):
    """
    Sync a local variable with a field in a Pydantic model:
    - If local_value is None, try to pull from model.
    - If local_value is not None, update model with it.
    - Update allObtainedParams with the field_name and local_value when local_value is not None.
    Returns the resolved value.
    """
    if local_value is None:
        local_value = getattr(params_model, field_name, None)
    else:
        setattr(params_model, field_name, local_value)
    if local_value is not None:
        allObtainedParams[field_name] = local_value
    return local_value
