#!/usr/bin/env python
"""
Test script for DynamicPromptV2 multi-language support
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/felipealbertuxd/knight-agent/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')
django.setup()

from rag.dynamic_prompt_v2 import DynamicPromptV2, get_prompt_builder


def test_language_support():
    """Test that all languages load properly"""
    languages = ['pt_BR', 'en_US', 'es_ES', 'sv_SE']
    
    print("Testing DynamicPromptV2 Multi-Language Support")
    print("=" * 50)
    
    for lang in languages:
        print(f"\n🌐 Testing language: {lang}")
        print("-" * 30)
        
        try:
            # Create prompt builder for this language
            prompt_builder = DynamicPromptV2(lang)
            
            # Get system prompt
            system_prompt = prompt_builder.get_system_prompt()
            
            # Check if prompt was loaded
            if system_prompt and len(system_prompt) > 50:
                print(f"✅ System prompt loaded successfully")
                print(f"   Length: {len(system_prompt)} characters")
                print(f"   Preview: {system_prompt[:100]}...")
            else:
                print(f"❌ System prompt is too short or empty")
            
            # Test context building
            test_context = prompt_builder.build_context(
                query="Como solicito férias?" if lang == 'pt_BR' else "How do I request vacation?",
                documents=[{"content": "Test document content"}],
                resources={
                    "links": [{"title": "Test Link", "url": "http://example.com", "ai_guidance": "Use for vacation"}]
                }
            )
            
            if test_context:
                print(f"✅ Context building successful")
                print(f"   Context length: {len(test_context)} characters")
            else:
                print(f"❌ Context building failed")
                
        except Exception as e:
            print(f"❌ Error loading language {lang}: {str(e)}")
    
    # Test language switching
    print("\n\n🔄 Testing Language Switching")
    print("-" * 30)
    
    try:
        # Get singleton instance
        prompt_builder = get_prompt_builder('pt_BR')
        initial_prompt = prompt_builder.get_system_prompt()
        print(f"✅ Initial language (pt_BR): {initial_prompt[:50]}...")
        
        # Switch language
        prompt_builder.switch_language('en_US')
        switched_prompt = prompt_builder.get_system_prompt()
        print(f"✅ Switched to en_US: {switched_prompt[:50]}...")
        
        # Verify they're different
        if initial_prompt != switched_prompt:
            print(f"✅ Language switching confirmed - prompts are different")
        else:
            print(f"⚠️  Warning: Prompts are the same after switching")
            
    except Exception as e:
        print(f"❌ Error testing language switching: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ Multi-language support test complete!")


if __name__ == "__main__":
    test_language_support()