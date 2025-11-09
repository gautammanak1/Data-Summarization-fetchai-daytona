import asyncio
from datetime import datetime
from uuid import uuid4

import os
from data_analyzer import run_data_analysis_sandbox, get_asi_llm_summary

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)

agent = Agent(
    name="data-summarization-agent",
    seed="data-summarization-agent-seed-daytona",
    port=8000,
    mailbox=True,
)

protocol = Protocol(spec=chat_protocol_spec)


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id),
    )

    # Extract plain text from chat content
    text = ""
    for part in msg.content:
        if isinstance(part, TextContent):
            text += part.text
    query = (text or "").strip()

    if not query or len(query) < 3:
        await ctx.send(
            sender,
            ChatMessage(
                timestamp=datetime.utcnow(),
                msg_id=uuid4(),
                content=[
                    TextContent(
                        type="text",
                        text="📊 Data Summarization Assistant\n\nPlease send data (CSV/JSON text, URL, or Google Sheets link):\n\nExamples:\n- URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit\n- CSV text: Product,Sales\nLaptop,1500\nPhone,2000\n- JSON URL: https://api.example.com/data.json",
                    )
                ],
            ),
        )
        return

    # Use the entire query as data input
    data_input = query.strip()

    loop = asyncio.get_running_loop()
    try:
        ctx.logger.info(f"Processing data analysis request. Data length: {len(data_input)}")
        
        # Run data analysis in sandbox
        sandbox_result = await loop.run_in_executor(
            None, 
            run_data_analysis_sandbox, 
            data_input
        )
        
        # Unpack tuple (sandbox, url, text_summary)
        sandbox, url, text_summary = (sandbox_result + (None,))[:3] if isinstance(sandbox_result, tuple) else (None, None, None)

        # Optional: refine summary using ASI LLM if key provided
        refined_summary = None
        if text_summary:
            asi_key = os.getenv('ASI_API_KEY')
            if asi_key:
                refined_summary = get_asi_llm_summary(asi_key, text_summary)

        if url:
            summary_block = f"\n\n📝 Summary (LLM):\n{refined_summary}" if refined_summary else (f"\n\n📝 Summary:\n{text_summary}" if text_summary else "")
            reply = (
                f"✅ Data analysis complete!\n\n"
                f"📊 Preview URL: {url}"
                f"\n\nThe analysis includes:\n- Summary statistics\n- Key insights\n- Standard visualizations (histograms, bar charts, correlation heatmaps)"
                f"{summary_block}"
                f"\n\nOpen the URL to view the full report."
            )
        else:
            reply = f"❌ Error: Could not analyze the data. Please check:\n- The data format is correct (CSV or JSON)\n- If using URL, it is accessible\n- If using Google Sheets, it is publicly accessible or shared with view permissions\n- The data is not empty"
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        ctx.logger.error(f"Error in data analysis: {error_details}")
        reply = f"❌ Error: {str(e)}\n\nPlease check the data format and try again."

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.utcnow(),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=reply)],
        ),
    )


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Acknowledged message {msg.acknowledged_msg_id} from {sender}")


agent.include(protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()

