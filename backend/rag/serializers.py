from rest_framework import serializers

class SearchQuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000)
    k = serializers.IntegerField(default=5, min_value=1, max_value=20)

class SearchResultSerializer(serializers.Serializer):
    content = serializers.CharField()
    score = serializers.FloatField()
    document_title = serializers.CharField()
    chunk_id = serializers.CharField()