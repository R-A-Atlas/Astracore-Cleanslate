from fastapi import HTTPException


def enforce_operator_binding(*, expected_operator_key: str, provided_operator_key: str, stage: str) -> None:
    if provided_operator_key != expected_operator_key:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Operator binding mismatch at {stage}: "
                "request operator does not match session owner"
            ),
        )
