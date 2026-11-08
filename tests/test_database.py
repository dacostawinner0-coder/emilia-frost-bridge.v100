from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from database import Database


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")
        await self.db.initialize()

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_accounts_are_isolated_by_guild(self):
        async with await self.db.connect() as connection:
            await connection.execute("INSERT INTO economy_accounts(guild_id,user_id,wallet) VALUES ('1','42',10),('2','42',90)")
            await connection.commit()
        first = await self.db.account(1, 42)
        second = await self.db.account(2, 42)
        self.assertEqual((first["wallet"], second["wallet"]), (10, 90))

    async def test_transfer_cannot_overdraw_under_concurrent_requests(self):
        async with await self.db.connect() as connection:
            await connection.execute("INSERT INTO economy_accounts(guild_id,user_id,wallet) VALUES ('1','10',100)")
            await connection.commit()
        results = await asyncio.gather(self.db.transfer(1, 10, 20, 80), self.db.transfer(1, 10, 30, 80))
        self.assertEqual(sum(results), 1)
        self.assertGreaterEqual((await self.db.account(1, 10))["wallet"], 0)

    async def test_daily_reward_is_single_claim(self):
        results = await asyncio.gather(*[self.db.claim_reward(1, 99, "daily", 200, 86400, 2_000_000_000) for _ in range(2)])
        self.assertEqual(sum(1 for ok, _ in results if ok), 1)

    async def test_bank_moves_are_atomic(self):
        await self.db.account(1, 42)
        async with await self.db.connect() as connection:
            await connection.execute("UPDATE economy_accounts SET wallet=100 WHERE guild_id='1' AND user_id='42'")
            await connection.commit()
        moved = await self.db.bank_move(1, 42, 75, True)
        self.assertTrue(moved)
        account = await self.db.account(1, 42)
        self.assertEqual((account["wallet"], account["bank"]), (25, 75))
        self.assertFalse(await self.db.bank_move(1, 42, 50, True))


if __name__ == "__main__":
    unittest.main()
