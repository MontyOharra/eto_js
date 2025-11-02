"""
Sentinel Value for Update Operations

Provides a sentinel value to distinguish between:
- Field not provided in update (UNSET)
- Field explicitly set to None (None)
- Field set to a value (any other value)

Usage in Update dataclasses:
```python
from shared.types._sentinel import UNSET, UnsetType

@dataclass
class MyModelUpdate:
    name: str | None | UnsetType = UNSET  # Can be: value, None, or UNSET
    age: int | UnsetType = UNSET           # Can be: value or UNSET
```

Usage in Repository update methods:
```python
from shared.types._sentinel import UNSET

def update(self, id: int, data: MyModelUpdate) -> MyModel:
    if data.name is not UNSET:
        model.name = data.name  # Will update even if data.name is None

    if data.age is not UNSET:
        model.age = data.age
```
"""


class UnsetType:
    """
    Singleton sentinel class for representing unset values.

    This is a unique object that can be used to distinguish between:
    - A field that was not provided (UNSET)
    - A field that was explicitly set to None (None)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


# Singleton instance
UNSET = UnsetType()


__all__ = ['UNSET', 'UnsetType']
