class Flow:
    _tracer: AgentTraceLogger  # Class attribute annotation

    def __init__(self, ...):
        self._tracer = AgentTraceLogger()
        super().__init__(...)  # Initialize the parent class
        # Additional initialization code...
        
    # Other methods of the Flow class...
