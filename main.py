import asyncio
import time
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field, NonNegativeFloat, PositiveInt

app = FastAPI(title="Async Calculator", version="1.0.0")

class NumberResult(BaseModel):
    number: int = Field(..., description="Исходное число")
    square: int = Field(..., description="Квадрат числа")
    delay: NonNegativeFloat = Field(..., description="Задержка в секундах")
    time: NonNegativeFloat = Field(..., description="Фактическое время выполнения операции в секундах")

class CalculateRequest(BaseModel):
    numbers: List[int] = Field(..., description="Список чисел для возведения в квадрат")
    delays: List[NonNegativeFloat] = Field(..., description="Список задержек для каждой операции в секундах")
    
    def validate_lengths(self):
        if len(self.numbers) != len(self.delays):
            raise ValueError("Длины списков numbers и delays должны совпадать")

class CalculateResponse(BaseModel):
    results: List[NumberResult]
    total_time: NonNegativeFloat
    parallel_faster_than_sequential: bool

async def calculate_square(number: int, delay: float) -> NumberResult:
    """
    Асинхронная функция, имитирующая долгую операцию вычисления.
    Использует asyncio.sleep, чтобы не блокировать поток.
    """
    start_time = time.monotonic()
    await asyncio.sleep(delay)
    end_time = time.monotonic()
    
    return NumberResult(
        number=number,
        square=number ** 2,
        delay=delay,
        time=round(end_time - start_time, 2)
    )

@app.post("/calculate/", response_model=CalculateResponse)
async def calculate(request: CalculateRequest):
    # Валидация входных данных
    request.validate_lengths()
    
    # 1. Асинхронное выполнение (параллельное с точки зрения ожидания I/O)
    start_total = time.monotonic()
    
    # Создаем список задач (корутин)
    tasks = [
        calculate_square(num, dly) 
        for num, dly in zip(request.numbers, request.delays)
    ]
    
    # asyncio.gather запускает все задачи одновременно и ждет их завершения
    results = await asyncio.gather(*tasks)
    
    end_total = time.monotonic()
    total_time = round(end_total - start_total, 2)

    # 2. Расчет гипотетического последовательного времени
    # Это сумма всех задержек, так как в реальности вычисление квадрата мгновенно
    sequential_time = sum(request.delays)
    
    # 3. Сравнение (с допуском на погрешность в 50 мс из-за накладных расходов асинхронности)
    is_faster = total_time < (sequential_time - 0.05)

    return CalculateResponse(
        results=results,
        total_time=total_time,
        parallel_faster_than_sequential=is_faster
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)