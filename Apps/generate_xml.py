import json
    
def convert_input_to_xml(input_file, defaults_file, output_file):

    def read_default_values_from_json(file_path):
        with open(file_path, 'r') as file:
            default_values = json.load(file)
        return default_values

    # Read default values from JSON file
    defaults = read_default_values_from_json(defaults_file)
    cluster_address = defaults['cluster_address']
    workers = defaults['workers']
    start_containers = defaults['start_containers']
    end_containers = defaults['end_containers']
    start_objects = defaults['start_objects']
    end_objects = defaults['end_objects']
    sizes = defaults['sizes']
    put = defaults['put']
    get = defaults['get']
    delete = defaults['delete']
    delay = defaults['delay']

    runtime = None
    totalOps = None
    totalBytes = None

    with open(input_file, 'r') as input_file:
        lines = iter(input_file)

        with open(output_file, 'w') as file:
            file.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
            file.write('<workload name="swift-sample" description="sample benchmark for swift">\n')
            file.write('  <storage type="swift" />\n')
            file.write('  <auth type="swauth" config="username=test:tester;password=testing;auth_url=http://{}/auth/v1.0" />\n'.format(cluster_address))
            file.write('  <workflow>\n\n')

            for line in lines:
                parts = line.strip().split(',')
                if len(parts) > 0:
                    command = parts[0]
                    params = parts[1:]

                    if command == 'init':

                        for item in params:
                            if item.startswith('workers'):
                                workers = item.split("=")[1]
                                break

                        for item in params:
                            if item.startswith('containers'):
                                start_containers = item.split("=")[1].split("-")[0]
                                end_containers = item.split("=")[1].split("-")[1]
                                break
                        
                        file.write('    <workstage name="init">\n')
                        file.write('      <work type="init" workers="{}" config="containers=r({},{})" />\n'.format(workers,start_containers,end_containers))
                        file.write('    </workstage>\n\n')

                    elif command == 'prepare':
                        
                        for item in params:
                            if item.startswith('workers'):
                                workers = item.split("=")[1]
                                break

                        for item in params:
                            if item.startswith('containers'):
                                start_containers = item.split("=")[1].split("-")[0]
                                end_containers = item.split("=")[1].split("-")[1]
                                break

                        for item in params:
                            if item.startswith('objects'):
                                start_objects = item.split("=")[1].split("-")[0]
                                end_objects = item.split("=")[1].split("-")[1]
                                break

                        for item in params:
                            if item.startswith('sizes'):
                                sizes = item.split("=")[1]
                                break

                        file.write('    <workstage name="prepare">\n')
                        file.write('      <work type="prepare" workers="{}" config="containers=r({},{});objects=r({},{});sizes=c({})KB" />\n'.format(workers,start_containers,end_containers,start_objects,end_objects,sizes))
                        file.write('    </workstage>\n\n')

                    elif command == 'main[':

                        file.write('    <workstage name="main">\n')
                        line = next(lines)

                        while "pgd" in line:
                            parts = line.strip().split(',')
                            params = parts

                            for item in params:
                                if item.startswith('workers'):
                                    workers = item.split("=")[1]
                                    break

                            for item in params:
                                if item.startswith('containers'):
                                    start_containers = item.split("=")[1].split("-")[0]
                                    end_containers = item.split("=")[1].split("-")[1]
                                    break

                            for item in params:
                                if item.startswith('objects'):
                                    start_objects = item.split("=")[1].split("-")[0]
                                    end_objects = item.split("=")[1].split("-")[1]
                                    break

                            for item in params:
                                if item.startswith('sizes'):
                                    sizes = item.split("=")[1]
                                    break

                            for item in params:
                                if item.startswith('pgd'):
                                    pgd = item.split("=")[1]
                                    put = pgd.split(' ')[0]
                                    get = pgd.split(' ')[1]
                                    delete = pgd.split(' ')[2]
                                    break

                            for item in params:
                                if item.startswith('runtime'):
                                    runtime = item.split("=")[1]
                                    break

                            for item in params:
                                if item.startswith('totalOps'):
                                    totalOps = item.split("=")[1]
                                    break

                            for item in params:
                                if item.startswith('totalBytes'):
                                    totalBytes = item.split("=")[1]
                                    break

                            if runtime:
                                operation = "runtime"
                                file.write('      <work name="main" workers="{}" {}="{}">\n'.format(workers, operation, runtime))
                            elif totalOps:
                                operation = "totalOps"
                                file.write('      <work name="main" workers="{}" {}="{}">\n'.format(workers, operation, totalOps))
                            elif totalBytes:
                                operation =  "totalBytes"
                                file.write('      <work name="main" workers="{}" {}="{}">\n'.format(workers, operation, totalBytes))
                            file.write('        <operation type="write" ratio="{}" config="containers=r({},{});objects=r({},{});sizes=c({})KB" />\n'.format(put, start_containers, end_containers, start_objects, end_objects, sizes))
                            file.write('        <operation type="read" ratio="{}" config="containers=r({},{});objects=r({},{})" />\n'.format(get, start_containers, end_containers, start_objects, end_objects))
                            file.write('        <operation type="delete" ratio="{}" config="containers=r({},{});objects=r({},{})" />\n'.format(delete, start_containers, end_containers, start_objects, end_objects))
                            file.write('      </work>\n')
                            line = next(lines)

                        file.write('    </workstage>\n\n')

                    elif command == 'cleanup':

                        for item in params:
                            if item.startswith('workers'):
                                workers = item.split("=")[1]
                                break

                        for item in params:
                            if item.startswith('containers'):
                                start_containers = item.split("=")[1].split("-")[0]
                                end_containers = item.split("=")[1].split("-")[1]
                                break

                        for item in params:
                            if item.startswith('objects'):
                                start_objects = item.split("=")[1].split("-")[0]
                                end_objects = item.split("=")[1].split("-")[1]
                                break

                        file.write('    <workstage name="cleanup">\n')
                        file.write('      <work type="cleanup" workers="{}" config="containers=r({},{});objects=r({},{})" />\n'.format(workers, start_containers, end_containers, start_objects, end_objects))
                        file.write('    </workstage>\n\n')

                    elif command == 'delay':
                        for item in params:
                            if item.startswith('time'):
                                delay = item.split("=")[1]
                        file.write('    <workstage name="delay" closuredelay="{}">\n'.format((delay)))
                        file.write('            <work name="delay" type="delay">\n')
                        file.write('                <operation type="delay"/>\n')
                        file.write('            </work>\n')
                        file.write('    </workstage>\n\n')

                    elif command == 'dispose':

                        for item in params:
                            if item.startswith('workers'):
                                workers = item.split("=")[1]
                                break

                        for item in params:
                            if item.startswith('containers'):
                                start_containers = item.split("=")[1].split("-")[0]
                                end_containers = item.split("=")[1].split("-")[1]
                                break

                        file.write('    <workstage name="dispose">\n')
                        file.write('      <work type="dispose" workers="{}" config="containers=r(1,{})" />\n'.format(workers, start_containers, end_containers))
                        file.write('    </workstage>\n\n')

            file.write('  </workflow>\n')
            file.write('</workload>\n')
