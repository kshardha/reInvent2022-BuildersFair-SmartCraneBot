import random
import logging
from flask import Flask

# create logger
logger = logging.getLogger('returncelebrityname')

mainNameList = ['Tom Cruise', 'Brad Pitt','Michael Jordan', 'Tom Hanks', 'Johnny Depp', 'Arnold Schwarzenegger', 'Jim Carrey',
'Emma Watson', 'Leonardo DiCaprio', 'Morgan Freeman', 'Tom Hanks', 'Serena Williams', 'Matt Damon', 'Al Pacino', 'Kate Winslet',
'Natalie Portman','Angelina Jolie', 'LeBron James', 'Scarlett Johansson', 'Anne Hathaway', 'Jessica Alba', 'Keira Knightley',
'Julia Roberts','Tom Brady', 'Keanu Reeves', 'Megan Fox', 'Steffi Graf', 'Robin Williams', 'Zach Galifianakis', 'Sandra Bullock',
'Jennifer Aniston', 'Emma Stone', 'Rachel McAdams', 'Roger Federer', 'Michael Phelps', 'Michael Schumacher', 'Tiger Woods', 'Muhammad Ali',
'Usain Bolt', 'Babe Ruth','Kobe Bryant', 'Peyton Manning','Billie Jean King']

nameList1 = mainNameList[:]
nameList2 = []
celebrityName = ""

#mainNameList = ['Tom Cruise', 'Brad Pitt','Michael Jordan', 'Tom Hanks']

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def GetCelebrityName():
    global nameList1
    global nameList2
    global mainNameList
    global celebrityName

    if (len(nameList1) != 0):
        print("---- from List 1 ----. Current count: " + str(len(nameList1)))
        logger.info("---- from List 1 ----. Current count: " + str(len(nameList1)))
        celebrityName = random.choice(nameList1) 
        print(celebrityName)
        logger.info(celebrityName)
        nameList1.remove(celebrityName)
        nameList2.append(celebrityName)
    elif(len(nameList2) != 0):
        print("---- from List 2 ----. Current count: " + str(len(nameList2)))
        logger.info("---- from List 2 ----. Current count: " + str(len(nameList2)))
        celebrityName = random.choice(nameList2) 
        print(celebrityName)
        logger.info(celebrityName)
        nameList2.remove(celebrityName)
    elif(len(nameList1) == 0):
        print("--- list 1 is empty. Assigning it back to the main name list ---")
        logger.info("--- list 1 is empty. Assigning it back to the main name list ---")
        nameList1 = mainNameList[:]
    
    return celebrityName


if __name__ == "__main__":
    #app.logger.setLevel(logging.INFO)
    app.run(host='0.0.0.0', port=80)

    