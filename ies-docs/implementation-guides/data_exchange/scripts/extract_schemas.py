import yaml
import json
import os
import datetime

def extract_schemas(spec_file, output_dir):
    print(f"Reading OpenAPI spec from {spec_file}...")
    with open(spec_file, "r") as f:
        spec = yaml.safe_load(f)
    
    # Load base spec for resolution
    base_spec_path = os.path.join(os.path.dirname(spec_file), "openadr3.yaml")
    with open(base_spec_path, "r") as f:
        base_spec = yaml.safe_load(f)
    
    schemas = spec.get("components", {}).get("schemas", {})
    if not schemas:
        print("No schemas found in components/schemas.")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    for name, schema in schemas.items():
        output_schema = {
            "$id": f"https://india-energy-stack.github.io/schemas/{name}.schema.json",
            **schema
        }
        
        def resolve_and_inline(obj, seen_refs=None):
            if seen_refs is None:
                seen_refs = set()
                
            if isinstance(obj, dict):
                # We iterate over a copy of items because we might delete/add keys
                for k, v in list(obj.items()):
                    if k == "$ref" and isinstance(v, str):
                        # Determine which spec to look in
                        target_spec = spec
                        ref_path_str = v
                        if v.startswith("openadr3.yaml"):
                            target_spec = base_spec
                            ref_path_str = v.split("#/")[-1]
                        elif v.startswith("#/"):
                            ref_path_str = v.split("#/")[-1]
                        else:
                            # External File Ref without hash (not common here)
                            continue
                            
                        # Avoid infinite loops
                        if v in seen_refs:
                            continue

                        # Navigate to the ref
                        def get_from_spec(s, path):
                            parts = [p for p in path.split("/") if p]
                            curr = s
                            for p in parts:
                                try:
                                    curr = curr[p]
                                except (KeyError, TypeError) as e:
                                    # Special handling for standard OAS structure 
                                    # if the spec object is slightly different
                                    raise KeyError(f"Missing key '{p}' in path '{path}'") from e
                            return curr

                        try:
                            try:
                                ref_obj = get_from_spec(target_spec, ref_path_str)
                            except (KeyError, TypeError):
                                # Fallback to base_spec if not found in current target
                                if target_spec is spec:
                                    ref_obj = get_from_spec(base_spec, ref_path_str)
                                else:
                                    raise
                            
                            # Replace ref with content
                            del obj[k]
                            # Copy to avoid side-effects (handle datetime objects from yaml)
                            def datetime_handler(x):
                                if isinstance(x, datetime.datetime):
                                    return x.isoformat()
                                raise TypeError("Unknown type")

                            ref_obj_copy = json.loads(json.dumps(ref_obj, default=datetime_handler))
                            obj.update(ref_obj_copy)
                            # Recursive call to handle nested refs (passing a new set with current ref)
                            resolve_and_inline(obj, seen_refs | {v})
                        except (KeyError, TypeError) as e:
                            print(f"Warning: Could not resolve ref {v} -> {e}")
                    else:
                        resolve_and_inline(v, seen_refs)
            elif isinstance(obj, list):
                for item in obj:
                    resolve_and_inline(item, seen_refs)

        resolve_and_inline(output_schema)
        
        output_path = os.path.join(output_dir, f"{name}.schema.json")
        with open(output_path, "w") as f:
            json.dump(output_schema, f, indent=2)
        print(f"Extracted (Inlined): {output_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, "..")
    extract_schemas(
        os.path.join(project_root, "specs", "attributes.yaml"),
        os.path.join(project_root, "specs", "extracted")
    )
