from statistics import median
import numpy as np

unique_ints = np.random.randint(100, 534, 50)

min_int, max_int = np.min(unique_ints), np.max(unique_ints)

med_int = median(unique_ints)

print(min_int, max_int, med_int)

unique_ints = np.sort(unique_ints)
print(unique_ints[::-1])