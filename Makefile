# The learnbook. Python 3.10+ only, no dependencies. TRACK picks the track (default: the first ready one).
TRACK ?= linux-ai-era
LB := python3 -m learnbook --track $(TRACK)
.PHONY: help play watch status list review quiz validate test book json tracks

help:            ## this list
	@grep -E '^[a-z0-9%-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n",$$1,$$2}'
	@echo "  lab01 ...    any lab target, run in tracks/$(TRACK) (make -C tracks/$(TRACK) help)"

play:            ## the browser game at http://127.0.0.1:8765
	$(LB) serve
watch:           ## rustlings mode: the next exercise, re-checked every time you save
	$(LB) watch
status:          ## progress for the current track
	$(LB) status
list:            ## every chapter and exercise with its state
	$(LB) list
review:          ## spaced review of questions that are due
	$(LB) review
quiz:            ## the delayed quiz (opens two days after your first cleared chapter)
	$(LB) quiz
tracks:          ## every track in the book, ready and planned
	$(LB) tracks
validate:        ## prove every exercise is gradable: broken files fail, solutions pass
	$(LB) validate
test: validate   ## validate plus the engine's unit tests
	python3 -m unittest discover -s tests
book:            ## the whole track as one Markdown file, BOOK.md
	$(LB) export md --out BOOK.md
json:            ## the whole track as JSON for other tools (no answers)
	$(LB) export json --out $(TRACK).json

lab%:            ## hands-on labs live in the track: make lab01, make lab06-up, ...
	$(MAKE) -C tracks/$(TRACK) $@
prereqs ollama agents sandbox-verify score:
	$(MAKE) -C tracks/$(TRACK) $@
