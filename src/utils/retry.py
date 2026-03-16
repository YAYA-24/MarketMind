"""重试工具，用于调用易限频的外部 API。"""

import time


def retry(func, *args, max_retries: int = 3, delay: float = 2, **kwargs):
    """指数退避重试。

    Args:
        func: 要调用的函数
        *args, **kwargs: 传给 func 的参数
        max_retries: 最大重试次数
        delay: 基础延迟（秒），实际延迟为 delay * (attempt + 1)
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise e
