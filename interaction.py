from gtts import gTTS

import settings


def say_my_name(persons, save_dir=settings.interactions_dir, play=False):
	for person in persons:
		phrase = "Hi, {0}!".format(person)
		myobj = gTTS(text=phrase, lang='en', slow=False)
		file_name="{0}/{1}.mp3".format(save_dir, person)
		myobj.save(file_name)
		# TODO: send audio to nest cam
		## No API provided for sending audio over so
		## Research if one can send audio/use mic via web
		## Check if this process can be easily automated
		## Reasearch how to send mp3 to mic input
		if play:
			os.system(file_name)

# TODO: post slack notification
## Send to a channel if a person detected within certain time frame
## Send to a channel if unknown person detected

# TODO: use Spotify API to play theme music of a person

# TODO: use Sigma API to send Merit
## Determine type of merits and data needed
## Collect data
## Integrate Sigma API

def interact(persons):
	say_my_name(persons, play=True)