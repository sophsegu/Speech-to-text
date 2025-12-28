### Backstory
As a hard of hearing person it can be difficult to watch certain content that does not come with closed captions. 
To help solve this issue I want to use my knowledge in computer science to create a program which takes in an mp3 file or records sounds and then transcribes them. 
The only disadvantage with this method is that some words can be unintelligble. I want to solve this issue using artificial intelligence, the transcribed text will be fed into AI
and using context clues will fill in the words that were not able to be determined earlier.

### How to run locally
Go to folder that contains the backend using command prompt and run py -m uvicorn Main:app --host 0.0.0.0 --port 8000 --reload
Go to folder that contains the frontend using command prompt and run py -m http.server 8000
Then in internet browser go to http://localhost:3000/index.html
