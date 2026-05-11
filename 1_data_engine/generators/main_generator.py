"""
Shadow Network Intelligence - Main Data Generator
Orchestrates generation of all synthetic fraud data
"""
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

class DataGenerator:
    def __init__(self, output_dir: str = "../outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.data = {
            "persons": [],
            "companies": [],
            "bank_accounts": [],
            "transactions": [],
            "relationships": [],
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator_version": "1.0.0"
            }
        }
    
    def generate_all(self, size: str = "small"):
        """Generate all data based on size parameter"""
        sizes = {
            "tiny": {"persons": 10, "companies": 5, "transactions": 50},
            "small": {"persons": 50, "companies": 20, "transactions": 500},
            "medium": {"persons": 200, "companies": 100, "transactions": 5000},
            "large": {"persons": 1000, "companies": 500, "transactions": 50000}
        }
        
        config = sizes.get(size, sizes["small"])
        
        print(f"Generating {size} dataset...")
        print(f"  Persons: {config['persons']}")
        print(f"  Companies: {config['companies']}")
        print(f"  Transactions: {config['transactions']}")
        
        self._generate_persons(config["persons"])
        self._generate_companies(config["companies"])
        self._generate_bank_accounts(config["persons"], config["companies"])
        self._generate_transactions(config["transactions"])
        self._generate_relationships()
        
        return self.data
    
    def _generate_persons(self, count: int):
        """Generate person entities"""
        first_names = ["James", "John", "Robert", "Michael", "William", "David", "Mary", "Patricia", "Jennifer", "Linda",
                       "Elena", "Viktor", "Dmitri", "Alexei", "Chen", "Wei", "Raj", "Priya", "Mohammed", "Fatima"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Martinez", "Anderson", "Taylor", "Thomas",
                      "Petrov", "Ivanov", "Wang", "Li", "Singh", "Kumar", "Al-Hassan", "Chen", "Kim", "Nguyen"]
        
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "Miami", "Seattle", "Denver", "Atlanta"]
        
        for i in range(count):
            self.data["persons"].append({
                "id": f"PERSON_{i:05d}",
                "name": f"{random.choice(first_names)} {random.choice(last_names)}",
                "ssn": f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
                "date_of_birth": (datetime(1960, 1, 1) + timedelta(days=random.randint(0, 15000))).strftime("%Y-%m-%d"),
                "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Maple', 'Cedar'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr'])}",
                "city": random.choice(cities),
                "state": random.choice(["NY", "CA", "TX", "FL", "IL"]),
                "zip": f"{random.randint(10000, 99999)}",
                "country": "US",
                "occupation": random.choice(["Engineer", "Manager", "Accountant", "Consultant", "Retail", "Healthcare"]),
                "risk_score": round(random.uniform(0, 1), 2),
                "created_at": datetime.now().isoformat()
            })
    
    def _generate_companies(self, count: int):
        """Generate company entities"""
        prefixes = ["Global", "American", "United", "National", "Pacific", "Atlantic", "Premier", "Capital", "Financial", "Investment"]
        suffixes = ["Corp", "Inc", "LLC", "Holdings", "Group", "Partners", "Enterprises", "Services", "Solutions", "Associates"]
        industries = ["Financial Services", "Import/Export", "Real Estate", "Consulting", "Technology", "Healthcare", "Construction", "Retail"]
        
        offshore = random.random() < 0.15
        
        for i in range(count):
            self.data["companies"].append({
                "id": f"COMPANY_{i:05d}",
                "name": f"{random.choice(prefixes)} {random.choice(suffixes)}",
                "ein": f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
                "industry": random.choice(industries),
                "incorporation_date": (datetime(2000, 1, 1) + timedelta(days=random.randint(0, 8000))).strftime("%Y-%m-%d"),
                "address": f"{random.randint(100, 9999)} Business Park {random.choice(['Way', 'Blvd', 'Circle'])}",
                "city": random.choice(["New York", "Wilmington", "Cayman Islands", "Zurich", "London", "Hong Kong"]),
                "state": random.choice(["NY", "DE", "FL", "CA"]),
                "country": "KY" if offshore else "US",
                "is_offshore": offshore,
                "annual_revenue": random.choice([50000, 100000, 500000, 1000000, 5000000]),
                "employee_count": random.randint(1, 500),
                "risk_score": round(random.uniform(0, 1), 2),
                "created_at": datetime.now().isoformat()
            })
    
    def _generate_bank_accounts(self, person_count: int, company_count: int):
        """Generate bank account entities"""
        account_types = ["CHECKING", "SAVINGS", "BUSINESS", "TRUST"]
        
        for i in range(min(person_count, 30)):
            self.data["bank_accounts"].append({
                "id": f"ACCOUNT_PERSON_{i:03d}",
                "account_number": f"{random.randint(100000, 999999)}{random.randint(100000, 999999)}",
                "routing_number": f"{random.randint(100000, 999999)}",
                "type": random.choice(account_types),
                "owner_type": "PERSON",
                "owner_id": f"PERSON_{i:05d}",
                "balance": round(random.uniform(0, 500000), 2),
                "currency": "USD",
                "opened_date": (datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2000))).strftime("%Y-%m-%d"),
                "status": "ACTIVE",
                "risk_score": round(random.uniform(0, 1), 2)
            })
        
        for i in range(min(company_count, 15)):
            self.data["bank_accounts"].append({
                "id": f"ACCOUNT_COMPANY_{i:03d}",
                "account_number": f"{random.randint(100000, 999999)}{random.randint(100000, 999999)}",
                "routing_number": f"{random.randint(100000, 999999)}",
                "type": "BUSINESS",
                "owner_type": "COMPANY",
                "owner_id": f"COMPANY_{i:05d}",
                "balance": round(random.uniform(0, 2000000), 2),
                "currency": "USD",
                "opened_date": (datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2000))).strftime("%Y-%m-%d"),
                "status": "ACTIVE",
                "risk_score": round(random.uniform(0, 1), 2)
            })
    
    def _generate_transactions(self, count: int):
        """Generate transaction entities"""
        transaction_types = ["WIRE", "ACH", "CASH", "CHECK"]
        
        accounts = [acc["id"] for acc in self.data["bank_accounts"]]
        
        for i in range(count):
            amount = round(random.uniform(100, 50000), 2)
            if random.random() < 0.1:
                amount = round(random.uniform(10000, 100000), 2)
            
            self.data["transactions"].append({
                "id": f"TXN_{i:07d}",
                "from_account": random.choice(accounts) if accounts else None,
                "to_account": random.choice(accounts) if accounts else None,
                "amount": amount,
                "currency": "USD",
                "type": random.choice(transaction_types),
                "date": (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
                "status": random.choice(["COMPLETED", "PENDING", "FLAGGED"]),
                "is_suspicious": random.random() < 0.05,
                "description": random.choice([
                    "Payment for services", "Invoice payment", "Transfer to savings",
                    "Wire transfer", "ACH payment", "Business expense"
                ])
            })
    
    def _generate_relationships(self):
        """Generate entity relationships"""
        for person in self.data["persons"][:10]:
            self.data["relationships"].append({
                "from_type": "PERSON",
                "from_id": person["id"],
                "relationship": "OWNS",
                "to_type": "COMPANY",
                "to_id": random.choice([c["id"] for c in self.data["companies"][:10]])
            })
    
    def save(self):
        """Save all data to output directory"""
        json_dir = self.output_dir / "json"
        json_dir.mkdir(exist_ok=True)
        
        output_file = json_dir / "synthetic_data.json"
        with open(output_file, "w") as f:
            json.dump(self.data, f, indent=2)
        
        print(f"Data saved to {output_file}")
        return str(output_file)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic fraud data")
    parser.add_argument("--size", choices=["tiny", "small", "medium", "large"], default="small",
                        help="Dataset size")
    parser.add_argument("--output", default="../outputs",
                        help="Output directory")
    
    args = parser.parse_args()
    
    generator = DataGenerator(output_dir=args.output)
    generator.generate_all(size=args.size)
    generator.save()
    
    print("Generation complete!")


if __name__ == "__main__":
    main()
