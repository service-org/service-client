#! -*- coding: utf-8 -*-
#
# author: forcemain@163.com

from __future__ import annotations

import typing as t

from http import HTTPStatus
from logging import getLogger
from inspect import getmembers
from service_green.core.green import urllib3
from service_client.exception import ClientError

logger = getLogger(__name__)


class BaseClient(object):
    """ 通用客户端基类 """

    def __init__(
            self,
            base_url: t.Optional[t.Text] = None,
            debug: t.Optional[bool] = None,
            pool_options: t.Optional[t.Dict[t.Text, t.Any]] = None
    ) -> None:
        """ 初始化实例

        @param base_url: 基础路径
        @param debug: 开启调试?
        @param pool_options: 池配置
        """
        self.debug = debug
        if base_url.endswith('/'):
            self.base_url = base_url.rstrip('/')
        else:
            self.base_url = base_url
        pool_options = pool_options or {}
        self.http = urllib3.PoolManager(**pool_options)

    def __new__(cls, *args: t.Any, **kwargs: t.Any) -> BaseClient:
        """ 创建客户端实例

        @param args  : 位置参数
        @param kwargs: 命名参数
        """
        instance = super(BaseClient, cls).__new__(cls)
        curr_client_instance = instance
        is_client_api = lambda o: isinstance(o, BaseClientAPI)

        def bind_sub_apis(client_api: BaseClientAPI) -> None:
            """ 绑定接口下的接口

            @param client_api: 客户端API对象
            @return: None
            """
            all_sub_apis = getmembers(client_api, predicate=is_client_api)
            for sub_api_name, sub_api in all_sub_apis:
                sub_api.client = client_api.client
                setattr(client_api, sub_api_name, sub_api)
                bind_sub_apis(sub_api)

        # 获取当前类中为BaseClientAPI实例的类属性
        all_apis = getmembers(cls, predicate=is_client_api)
        for name, api in all_apis:
            # 向子API实例传递客户端CLIENT实例
            api.client = instance
            setattr(instance, name, api)
            bind_sub_apis(api)
        else:
            return curr_client_instance

    def get(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        method = 'GET'
        return self.request(method, url, **kwargs)

    def post(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        method = 'POST'
        return self.request(method, url, **kwargs)

    def put(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        method = 'PUT'
        return self.request(method, url, **kwargs)

    def patch(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        method = 'PATCH'
        return self.request(method, url, **kwargs)

    def delete(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        method = 'DELETE'
        return self.request(method, url, **kwargs)

    def request(self, method: t.Text, url: t.Text, **kwargs: t.Any) -> t.Any:
        """ 请求处理方法

        :param method: 请求方法
        :param url: 请求地址
        :param kwargs: 请求参数
        :return: t.Any
        """
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30.0
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        if 'retries' not in kwargs:
            kwargs['retries'] = 3
        if 'base_url' in kwargs and kwargs['base_url']:
            base_url = kwargs.pop('base_url')
        else:
            base_url = self.base_url
        req_url = url if url.startswith(('http', 'https')) else f'{base_url}{url}'
        rsp = self.http.request(method, req_url, **kwargs)
        data = rsp.data.decode('utf-8')
        self.debug and logger.debug(f'{method} {req_url} with {kwargs}, resp={data}')
        if (
                HTTPStatus.OK.value
                <= rsp.status <
                HTTPStatus.MULTIPLE_CHOICES.value
        ):
            return rsp
        raise ClientError(data, original=req_url)


class BaseClientAPI(object):
    """ 客户端接口基类 """

    def __init__(self, client: t.Optional[BaseClient] = None) -> None:
        """ 初始化实例

        @param client: 客户端
        """
        self.client = client

    @property
    def _base_url(self) -> t.Text:
        return self.base_url if hasattr(self, 'base_url') else self.client.base_url

    def _get(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        hasattr(self, 'base_url') and kwargs.update({'base_url': self.base_url})
        return self.client.get(url, **kwargs)

    def _post(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        hasattr(self, 'base_url') and kwargs.update({'base_url': self.base_url})
        return self.client.post(url, **kwargs)

    def _put(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        hasattr(self, 'base_url') and kwargs.update({'base_url': self.base_url})
        return self.client.put(url, **kwargs)

    def _patch(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        hasattr(self, 'base_url') and kwargs.update({'base_url': self.base_url})
        return self.client.patch(url, **kwargs)

    def _delete(self, url: t.Text, **kwargs: t.Any) -> t.Any:
        hasattr(self, 'base_url') and kwargs.update({'base_url': self.base_url})
        return self.client.delete(url, **kwargs)
