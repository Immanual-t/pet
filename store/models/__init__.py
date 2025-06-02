# File: store/models/__init__.py
# Final corrected version with proper class names

from .product import Product
from .category import Category
from .customer import Customer
from .orders import Order
from .boarding import PetBoardingBooking, PetBoardingSlot
from .pet_media import PetMedia, MediaViewLog
from .slider import SliderImage  # Correct class name
from .review import CustomerReview  # Correct class name

# Import training models
try:
    from .training import PetTrainingBooking, PetTrainingSlot, PetTrainingProgram, PetTrainingProgress
    print("✅ Training models imported successfully")
except ImportError as e:
    print(f"❌ Training models import failed: {e}")
    print("Please make sure store/models/training.py exists with the training models")