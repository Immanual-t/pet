from django.db import models

class CustomerReview(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='reviews/')
    feedback = models.TextField()
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])


    def __str__(self):
        return self.name
