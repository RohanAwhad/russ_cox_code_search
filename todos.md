- [ ] Update the prompt to have a cmd like 'vv' which will only prompt the language model to add logging statements at the relevant places. Not through out the entire code, just for the particular function or error.
    - [ ] Brainstorm prompt
- [ ] Add examples where in there are consecutive updates to the same file and probably in the same place. Claude messes up there.
- [ ] Allow multiple generations to run simultaneously because the task is getting complicated and one models solution might not answer it. And i want to be prepared for that by generating solutions for the same prompt but from different models. 
- [ ] Addition of diffs. This way model knows what changed over the past commits. This way they dont redo the same thing again and again.
    - Should try out on my own how potential this is.
- [ ] Replace telescope grep, with my grep
- [ ] Having like a linter just run and dump a few errors would be nice.  

## Research:
- [ ] Generating docstrings for scripts, and then using them for figuring out which code files to put in context

---

# Done

- [x] Show the generation progress on the bottom left, just like neuralgate because now the cursor doesn't follow generation, and because of which it becomes difficult to know if generation is done or not.


