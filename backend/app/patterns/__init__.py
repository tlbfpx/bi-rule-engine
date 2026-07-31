"""设计模式基础设施模块 — 23 种设计模式的核心抽象

本包提供以下模式的泛型/抽象基础设施：
- Factory（工厂）
- Builder（建造者）
- Strategy（策略）
- Chain of Responsibility（责任链）
- Observer（观察者 / 事件总线）
- Command（命令）
- Template Method（模板方法）
- State（状态机）
- Decorator（装饰器）
- Mediator（中介者）
- Proxy（代理）
- Singleton（单例元类）
"""
from app.patterns.builder import IBuilder, RuleConfigBuilder
from app.patterns.chain import HandlerChain, IHandler
from app.patterns.command import CommandInvoker, ICommand
from app.patterns.decorator import IService, LoggingDecorator, MetricsDecorator
from app.patterns.factory import FactoryRegistry, IFactory
from app.patterns.mediator import IMediator, Mediator
from app.patterns.observer import Event, EventBus, IEventListener
from app.patterns.proxy import CachedProxy, IProxy
from app.patterns.singleton import Singleton
from app.patterns.state_machine import State, StateMachine
from app.patterns.strategy import IStrategy, StrategyRegistry
from app.patterns.template import BaseTemplate

__all__ = [
    "BaseTemplate",
    "CachedProxy",
    "CommandInvoker",
    "Event",
    "EventBus",
    "FactoryRegistry",
    "HandlerChain",
    "IBuilder",
    "ICommand",
    "IEventListener",
    "IFactory",
    "IHandler",
    "IMediator",
    "IProxy",
    "IService",
    "IStrategy",
    "LoggingDecorator",
    "Mediator",
    "MetricsDecorator",
    "RuleConfigBuilder",
    "Singleton",
    "State",
    "StateMachine",
    "StrategyRegistry",
]
