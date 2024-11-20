import discord

class MultiLineModal(discord.ui.Modal):
    def __init__(self, future):
        super().__init__(title="Paste CSV Data")

        self.future = future

        # Add a multi-line text input field
        self.csv_data = discord.ui.TextInput(
            label="Paste your CSV data here:",
            style=discord.TextStyle.paragraph,
            placeholder="wallet_address\ntoken_address\n...",
            required=True,
            max_length=2000  # Adjust as needed
        )
        self.add_item(self.csv_data)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # Acknowledge the interaction to prevent timeout

        # Extract the CSV data from the text input
        csv_text = self.csv_data.value

        # Set the result of the future to the CSV text
        self.future.set_result(csv_text)