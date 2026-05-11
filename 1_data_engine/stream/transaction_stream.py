"""
Shadow Network Intelligence - Live Transaction Stream
Simulates real-time transaction stream for demo purposes
"""
import asyncio
import json
import random
from datetime import datetime
from typing import Dict, List, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class TransactionStream:
    """
    Simulates a live stream of financial transactions.
    
    Generates transactions based on fraud patterns and normal activity
    for testing and demonstration purposes.
    """
    
    TRANSACTION_TYPES = ["WIRE", "ACH", "CASH", "CHECK"]
    
    NORMAL_AMOUNTS = [100, 500, 1000, 2500, 5000, 7500]
    SUSPICIOUS_AMOUNTS = [9500, 9800, 9900, 15000, 25000, 50000]
    
    def __init__(self, fraud_ratio: float = 0.1):
        self.fraud_ratio = fraud_ratio
        self.subscribers: List[Callable] = []
        self.running = False
        self.transaction_count = 0
    
    def subscribe(self, callback: Callable):
        """Subscribe to transaction stream"""
        self.subscribers.append(callback)
        logger.info(f"New subscriber added. Total: {len(self.subscribers)}")
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from transaction stream"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    async def start_stream(self, interval: float = 2.0):
        """
        Start generating transactions.
        
        Args:
            interval: Seconds between transactions
        """
        self.running = True
        logger.info("Transaction stream started")
        
        while self.running:
            transaction = self._generate_transaction()
            self.transaction_count += 1
            
            await self._broadcast(transaction)
            
            await asyncio.sleep(interval)
    
    def stop_stream(self):
        """Stop the transaction stream"""
        self.running = False
        logger.info("Transaction stream stopped")
    
    def _generate_transaction(self) -> Dict:
        """Generate a single transaction"""
        is_suspicious = random.random() < self.fraud_ratio
        
        if is_suspicious:
            amount = random.choice(self.SUSPICIOUS_AMOUNTS)
            txn_type = "WIRE" if random.random() < 0.5 else "CASH"
        else:
            amount = random.choice(self.NORMAL_AMOUNTS)
            txn_type = random.choice(self.TRANSACTION_TYPES)
        
        return {
            "id": f"TXN_{self.transaction_count + 1:07d}",
            "from_account": f"ACC_{random.randint(100, 999):03d}",
            "to_account": f"ACC_{random.randint(100, 999):03d}",
            "amount": amount,
            "currency": "USD",
            "type": txn_type,
            "date": datetime.now().isoformat(),
            "status": "COMPLETED",
            "is_suspicious": is_suspicious,
            "is_stream": True
        }
    
    async def _broadcast(self, transaction: Dict):
        """Broadcast transaction to all subscribers"""
        for subscriber in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(transaction)
                else:
                    subscriber(transaction)
            except Exception as e:
                logger.error(f"Error broadcasting to subscriber: {e}")
    
    def generate_batch(self, count: int) -> List[Dict]:
        """
        Generate a batch of transactions at once.
        
        Args:
            count: Number of transactions to generate
            
        Returns:
            List of transactions
        """
        return [self._generate_transaction() for _ in range(count)]
    
    def get_stats(self) -> Dict:
        """Get stream statistics"""
        return {
            "running": self.running,
            "total_generated": self.transaction_count,
            "subscribers": len(self.subscribers)
        }


async def stream_demo():
    """Demo function to show transaction streaming"""
    stream = TransactionStream(fraud_ratio=0.15)
    
    def print_transaction(txn):
        flag = " [SUSPICIOUS]" if txn["is_suspicious"] else ""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {txn['id']}: ${txn['amount']} ({txn['type']}){flag}")
    
    stream.subscribe(print_transaction)
    
    print("Starting 10-second demo stream...")
    stream.running = True
    
    for _ in range(10):
        txn = stream._generate_transaction()
        stream.transaction_count += 1
        print_transaction(txn)
        await asyncio.sleep(1)
    
    print(f"\nGenerated {stream.transaction_count} transactions")
    
    return stream


if __name__ == "__main__":
    asyncio.run(stream_demo())
