Blocking and Async code in Python
----------------------
These are relatively advanced concepts, but I'll give you a rundown.

Blocking code is when all other functions in your code stop executing because there is one currently running. For example -
```python
while True:
    print('Running')
```
This is an example of blocking code, as long as your program is running, this function will print `Running`, even if you put coder after this, it will not be executed.

Asynchronous code is when your code waits for a function to complete, and in that time, runs other functions.

Let's take the example of `requests` and `aiohttp`. Requests is blocking, aiohttp is async, what do those mean?

To put it simply, when you make a request using the `Requests` module, your code stops everything, and *waits* for a response from the server. None of your other functions will run while you send a request, if the server is down, for example, then your code will not do anything until the connection times itself out, which is incredibly inefficient and needlessly slows down code. The `aiohttp` module on the other hand, sends a request, and stops running code *inside that function* until it recieves a response. That means, if one function is sending requests, none of my other functions will be affected. This makes asynchronous code much better because it simply doesn't drop everything and wait for something to finish happening.

