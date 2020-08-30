summa = 2_000_000

years = 10
months = years * 12
percent_per_year = 6

for i in range(months):
    summa *= 1 + percent_per_year / 12 / 100

print(summa)
