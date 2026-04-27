import json
import yaml
import os
from jsonschema import validate, RefResolver

def validate_jsonld(sample_path, schema_path, base_spec_path):
    print(f"Validating {sample_path} against {schema_path}...")
    
    with open(sample_path, 'r') as f:
        data = json.load(f)
    
    # Handle list of instances or single instance
    instances = data if isinstance(data, list) else [data]
    
    with open(schema_path, 'r') as f:
        schema = json.load(f)
        
    with open(base_spec_path, 'r') as f:
        base_spec = yaml.safe_load(f)
        
    extracted_dir = os.path.dirname(schema_path)
    store = {
        f"https://india-energy-stack.github.io/schemas/{os.path.basename(schema_path)}": schema,
        f"file://{os.path.abspath(os.path.join(extracted_dir, '..', 'openadr3.yaml'))}": base_spec,
        "openadr3.yaml": base_spec
    }
    
    for f_name in os.listdir(extracted_dir):
        if f_name.endswith(".schema.json"):
            with open(os.path.join(extracted_dir, f_name), 'r') as f_obj:
                store[f_name] = json.load(f_obj)

    resolver = RefResolver(base_uri=f"file://{os.path.abspath(extracted_dir)}/", referrer=schema, store=store)
    
    try:
        for instance in instances:
            validate(instance=instance, schema=schema, resolver=resolver)
        print(f"SUCCESS: {sample_path} is valid.")
    except Exception as e:
        print(f"FAILURE: {sample_path} failed validation.")
        print(e)
        raise e

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, "..")
    specs_dir = os.path.join(project_root, "specs")
    extracted_dir = os.path.join(specs_dir, "extracted")
    examples_dir = os.path.join(project_root, "examples")
    bootcamp_dir = os.path.join(project_root, "bootcamp")
    
    base_spec = os.path.join(specs_dir, "openadr3.yaml")

    print("\n--- Validating Examples ---")
    validate_jsonld(
        os.path.join(examples_dir, "telemetry_report_example.jsonld"),
        os.path.join(extracted_dir, "IES_Report.schema.json"),
        base_spec
    )
    validate_jsonld(
        os.path.join(examples_dir, "tariff_specification_example.jsonld"),
        os.path.join(extracted_dir, "IES_Policy.schema.json"),
        base_spec
    )

    if os.path.exists(bootcamp_dir):
        print("\n--- Validating Bootcamp Data ---")
        # Validate Programs
        validate_jsonld(
            os.path.join(bootcamp_dir, "programs.jsonld"),
            os.path.join(extracted_dir, "IES_Program.schema.json"),
            base_spec
        )
        # Validate Policies
        validate_jsonld(
            os.path.join(bootcamp_dir, "policies.jsonld"),
            os.path.join(extracted_dir, "IES_Policy.schema.json"),
            base_spec
        )
        # Validate Telemetry Chunks
        for i in range(1, 11):
            validate_jsonld(
                os.path.join(bootcamp_dir, f"telemetry_chunk_{i}.jsonld"),
                os.path.join(extracted_dir, "IES_Report.schema.json"),
                base_spec
            )
