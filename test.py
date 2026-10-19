import bot
import discord

import unittest
from unittest.mock import patch, MagicMock, AsyncMock


class TestNotify(unittest.IsolatedAsyncioTestCase):
    @patch('discord.Client.get_user')
    async def test_notify(self, mock_get_user):
        mock_user = MagicMock()
        mock_user.send = AsyncMock()
        mock_get_user.return_value = mock_user

        await bot.notify("123", "TestSlot", 21)
        mock_user.send.assert_awaited_once_with("TestSlot has 21 new checks.")

    @patch('discord.Client.get_user', return_value=None)
    async def test_notify_user_not_found(self, mock_get_user):
        await bot.notify("123", "TestSlot", 21)

        mock_get_user.assert_called_once_with(123)

unittest.main()
