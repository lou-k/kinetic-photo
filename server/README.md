# Developing

First create the virtual environment:
```
pipenv install --dev
```

If you are running ubunto 24.04 and get the following error:
```
AttributeError: install_layout. Did you mean: 'install_platlib'
```
then:
* Comment out `uwgsi` from `Pipfile`
* Run `pipenv install --dev`
* Un-comment `uwgsi` from `Pipfile`
* Run `pipenv install`