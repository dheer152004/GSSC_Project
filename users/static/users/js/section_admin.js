(function($) {
    $(document).ready(function () {
        const $school = $('#id_school');
        const $department = $('#id_department');
        const $mentor = $('#id_mentor');

        function resetAndDisable($field) {
            $field.html('<option value="">---------</option>');
            $field.prop('disabled', true);
        }

        function enable($field) {
            $field.prop('disabled', false);
        }

        function fetchAndPopulate(url, data, $field, labelBuilder) {
            $.ajax({
                url: url,
                data: data,
                success: function (response) {
                    const items = Object.values(response)[0];
                    $field.html('<option value="">---------</option>');
                    items.forEach(function (item) {
                        const label = typeof labelBuilder === 'function'
                            ? labelBuilder(item)
                            : item.name;
                        $field.append(new Option(label, item.id));
                    });
                    enable($field);
                },
                error: function () {
                    resetAndDisable($field);
                }
            });
        }

        // When school changes, update departments
        $school.change(function () {
            const schoolId = $(this).val();
            resetAndDisable($department);
            resetAndDisable($mentor);

            if (schoolId) {
                fetchAndPopulate('/admin/users/section/load-departments/', { school_id: schoolId }, $department);
            }
        });

        // When department changes, update mentors
        $department.change(function () {
            const departmentId = $(this).val();
            resetAndDisable($mentor);

            if (departmentId) {
                fetchAndPopulate('/admin/users/section/load-mentors/', { department_id: departmentId }, $mentor, function (item) {
                    return item.name;
                });
            }
        });
    });
})(django.jQuery);
