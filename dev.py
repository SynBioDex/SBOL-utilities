all_namespaces = ["grace", "graceful",
           "disgraceful", "gracefully"]

stem = "gro"

# print(all(x == all_namespaces[0] for x in all_namespaces))

print(all(stem in namespace for namespace in all_namespaces))