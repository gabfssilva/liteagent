import inspect
import logging

import structlog


def add_file_prefix_to_event(_, __, event_dict):
    """
    A simple processor that prepends the filename to the event field.
    """
    frame = inspect.currentframe()
    try:
        for frameinfo in inspect.getouterframes(frame, 2):
            filepath = frameinfo.filename

            if 'structlog' in filepath or filepath.endswith('logger.py'):
                continue

            if 'liteagent' in filepath:
                rel_path = filepath.split('liteagent/')[-1]
                if rel_path.endswith('.py'):
                    rel_path = rel_path[:-3]

                module_path = rel_path.replace('/', '.')

                if 'providers/' in rel_path:
                    parts = module_path.split('.')
                    if len(parts) >= 3 and parts[-1] == 'provider':
                        module_path = parts[-2]

                event = event_dict.get('event', '')
                if event:
                    event_dict['event'] = f"{module_path}.{event}"
                return event_dict

    except (IndexError, AttributeError) as e:
        event_dict['_file_prefix_error'] = str(e)
    finally:
        del frame

    return event_dict


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_file_prefix_to_event,  # Our custom processor 
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False
)

log = structlog.get_logger()
