class Flow:
    _tracer: AgentTraceLogger | None = None

    def __init__(self, *args, **kwargs):
        # Initialize _tracer before calling super()
        super().__init__(*args, **kwargs)
