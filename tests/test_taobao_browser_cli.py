import pytest
from taobao.browser.cli import build_arg_parser, config_from_args

def test_parser_options():
 p=build_arg_parser(); a=p.parse_args(["--keyword","x","--keyword","y","--pages","2","--from-tasks","--cookie-file","c.txt","--db","x.db","--headless","--min-delay","1","--max-delay","2","--search-only"])
 assert a.keyword==["x","y"]; assert a.pages==2 and a.from_tasks and a.headless and a.search_only
 c=config_from_args(a); assert c.page_limit==2 and c.delay_policy.min_seconds==1

def test_default_pages():
 a=build_arg_parser().parse_args(["--keyword","x"]); assert a.pages==3 and not a.headless

def test_invalid_delay():
 a=build_arg_parser().parse_args(["--keyword","x","--min-delay","3","--max-delay","1"])
 with pytest.raises(ValueError): config_from_args(a)

def test_empty_mode_allowed_for_help():
 a=build_arg_parser().parse_args([]); assert a.keyword==[]
