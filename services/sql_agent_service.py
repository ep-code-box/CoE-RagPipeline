import os
import logging
from typing import Dict, Any, Optional

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

class SQLAgentService:
    def __init__(self):
        self.db_uri = (
            f"mysql+pymysql://{os.getenv("DB_USER", "coe_user")}:"
            f"{os.getenv("DB_PASSWORD", "coe_password")}@"
            f"{os.getenv("DB_HOST", "mariadb")}:"
            f"{os.getenv("DB_PORT", "3306")}/"
            f"{os.getenv("DB_NAME", "coe_db")}"
        )
        self.db = SQLDatabase.from_uri(self.db_uri)
        
        # LLM 초기화
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        )

        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        self.tools = self.toolkit.get_tools()

        # SQL Agent 프롬프트 정의
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant that can answer questions about the database schema and data. "
                       "You have access to the following tools:\n\n{tools}\n\n" 
                       "Use the following format:\n\n" 
                       "Question: the input question you must answer\n" 
                       "Thought: you should always think about what to do\n" 
                       "Action: the action to take, should be one of [{tool_names}]\n" 
                       "Action Input: the input to the action\n" 
                       "Observation: the result of the action\n" 
                       "... (this Thought/Action/Action Input/Observation can repeat N times)\n" 
                       "Thought: I now know the final answer\n" 
                       "Final Answer: the final answer to the original input question"),
            ("placeholder", "{agent_scratchpad}"),
            ("human", "{input}")
        ])

        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    async def run_sql_query(self, query: str) -> Dict[str, Any]:
        """
        자연어 쿼리를 SQL로 변환하고 실행하여 결과를 반환합니다.
        """
        try:
            response = await self.agent_executor.ainvoke({"input": query})
            return {"status": "success", "result": response["output"]}
        except Exception as e:
            logger.error(f"SQL Agent 실행 중 오류 발생: {e}")
            return {"status": "error", "message": str(e)}

