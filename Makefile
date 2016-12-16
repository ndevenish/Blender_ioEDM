all:

zip:
	rm io_EDM.zip
	zip -r io_EDM.zip io_EDM -x '*/__pycache__/*'
