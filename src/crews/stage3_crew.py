class Stage3Crew:
    def __init__(self, topic: str):
        self.topic = topic

    def kickoff(self) -> dict:
        article_text = (
            f"This is a detailed article on {self.topic}. " * 20
        )  # repeating the sentence to exceed 500 chars
        chart_data = {"data": []}  # dummy chart data
        return {"article": article_text, "chart_data": chart_data}
