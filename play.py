import asyncio
import argparse
from loguru import logger

# first-party
from src.indexer import index_project, index_project_semantic, load_existing_embeddings
from src.embedder import AsyncEmbedderClient


async def main():
    parser = argparse.ArgumentParser(description='Index and search code')
    parser.add_argument('project_path', type=str, help='Path to the project directory')
    parser.add_argument('--trigram', action='store_true', help='Use trigram indexing')
    parser.add_argument('--semantic', action='store_true', help='Use semantic indexing')
    parser.add_argument('--watch', action='store_true', help='Watch for file changes')
    args = parser.parse_args()

    project_path = args.project_path
    
    # Default to both if neither specified
    if not args.trigram and not args.semantic:
        args.trigram = True
        args.semantic = True
    
    # Initialize indices
    trigram_searcher = None
    trigram_mapping = None
    trigram_observer = None
    docstrings = None
    semantic_observer = None
    
    # Run trigram indexing if requested
    if args.trigram:
        logger.info("Starting trigram indexing...")
        trigram_searcher, trigram_mapping, trigram_observer = index_project(
            project_path, 
            watch=args.watch
        )
        logger.info("Trigram indexing complete")
    
    # Run semantic indexing if requested
    if args.semantic:
        logger.info("Starting semantic indexing...")
        embedder_host = "localhost"
        embedder_port = 8000
        
        try:
            docstrings, semantic_observer = await index_project_semantic(
                project_path,
                embedder_host=embedder_host,
                embedder_port=embedder_port,
                watch=args.watch
            )
        except Exception as e:
            logger.error(f"Error during semantic indexing: {str(e)}")
            # Continue with just trigram search if semantic fails
            docstrings = load_existing_embeddings(project_path)
    
    embedder = AsyncEmbedderClient()
    
    # Start interactive search interface
    try:
        while True:
            print("\n=== Code Search Interface ===")
            print("1. Trigram regex search")
            print("2. Semantic search")
            print("3. Exit")
            
            choice = input("Enter choice (1-3): ").strip()
            
            if choice == "1" and trigram_searcher:
                query = input("Enter regex pattern: ").strip()
                if not query:
                    continue
                    
                results = trigram_searcher.search(query)
                
                print(f"\nFound {len(results)} matches:")
                for idx, doc_id in enumerate(results[:10], 1):
                    print(f"{idx}. {trigram_mapping[doc_id]}")
                    
            elif choice == "2" and docstrings:
                query = input("Enter semantic search query: ").strip()
                if not query:
                    continue
                    
                results = await embedder.similarity_search(query, docstrings)
                
                print("\nTop matching files:")
                for i, result in enumerate(results, 1):
                    print(f"{i}. {result['filepath']} (score: {result['similarity']:.4f})")
                    
            elif choice == "3":
                break
                
            else:
                if choice not in ["1", "2", "3"]:
                    print("Invalid choice. Please enter 1, 2, or 3.")
                elif choice == "1" and not trigram_searcher:
                    print("Trigram index not available.")
                elif choice == "2" and not docstrings:
                    print("Semantic index not available.")
    
    except KeyboardInterrupt:
        print("\nSearch terminated by user")
    finally:
        # Clean up resources
        if trigram_observer:
            trigram_observer.stop()
            trigram_observer.join()
        if semantic_observer:
            semantic_observer.stop()
            semantic_observer.join()
        await embedder.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

