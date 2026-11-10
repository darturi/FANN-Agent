"""Fail immediately if any study phase tries to import a provider client."""
import importlib.abc
import sys


class NoModels(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='fannagent.model' or fullname.split('.')[0] in {'openai','anthropic','litellm','minisweagent'}:
            raise RuntimeError('Provider/model imports are forbidden in this study: '+fullname)


def enforce():
    sys.meta_path.insert(0,NoModels())
