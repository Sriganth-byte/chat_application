"""
Base repository class for data access abstraction.
"""
from typing import TypeVar, Optional, List, Any
from django.db import models
from django.db.models import QuerySet

T = TypeVar('T', bound=models.Model)


class RepositoryBase(Generic[T]):
    """Base repository for all models."""
    
    model_class: type
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID."""
        try:
            return self.model_class.objects.get(id=id)
        except self.model_class.DoesNotExist:
            return None
    
    def get_all(self) -> QuerySet[T]:
        """Get all entities."""
        return self.model_class.objects.all()
    
    def filter(self, **kwargs) -> QuerySet[T]:
        """Filter entities."""
        return self.model_class.objects.filter(**kwargs)
    
    def create(self, **kwargs) -> T:
        """Create new entity."""
        return self.model_class.objects.create(**kwargs)
    
    def update(self, id: int, **kwargs) -> int:
        """Update entity, returns rows affected."""
        return self.model_class.objects.filter(id=id).update(**kwargs)
    
    def delete(self, id: int) -> int:
        """Delete entity, returns rows affected."""
        return self.model_class.objects.filter(id=id).delete()[0]


from typing import Generic