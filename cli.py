import sys
from query import QueryProcessor

def main():
    print("Initializing Search Engine...")
    try:
        qp = QueryProcessor()
    except Exception as e:
        print(f"Error initializing: {e}")
        print("Did you run build.py?")
        return

    print("Search Engine Ready. Type 'exit' to quit.")
    
    while True:
        try:
            try:
                query_str = input("\nEnter Query: ")
            except EOFError:
                print("\nExiting...")
                break
                
            if query_str.strip().lower() in ["exit", "quit"]:
                break
            
            if not query_str.strip():
                continue
                
            results, _ = qp.process_query(query_str)
            
            print(f"Found {len(results)} results.")
            for i, res in enumerate(results[:5]): # Show top 5
                print(f"{i+1}. [{res['score']:.4f}] {res['id']}")
                print(f"   Path: {res['path']}")
                print(f"   Snippet: {res['snippet']}")
                print("-" * 40)
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error processing query: {e}")

if __name__ == "__main__":
    main()
