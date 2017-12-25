from gtts import gTTS

import settings


def say_my_name(persons, save_dir=settings.interactions_dir, play=False):
	for person in persons:
		phrase = "Hi, {0}!".format(person)
		myobj = gTTS(text=phrase, lang='en', slow=False)
		file_name="{0}/{1}.mp3".format(save_dir, person)
		myobj.save(file_name)
		#TODO: sent audio to nest cam
		if play:
			os.system(file_name)


def interact(persons):
	say_my_name(persons, play=True)